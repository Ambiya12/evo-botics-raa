#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http.client import responses
import json
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from evo_reception_interfaces.srv import ValidateQr
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from evo_reception.qr_integration import (
    QrValidationOutcome,
    extract_decoded_text,
    outcome_from_error_code,
    successful_validation_data,
    validate_backend_configuration,
)


@dataclass(frozen=True)
class BridgeValidation:
    outcome: QrValidationOutcome
    message: str
    destination_id: str = ""
    reservation: Optional[dict[str, Any]] = None
    error_code: Optional[str] = None


class QrReservationBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("qr_reservation_bridge_node")

        self.qr_detections_topic = self.declare_parameter(
            "qr_detections_topic", "/vision/qr/detections"
        ).value
        self.status_topic = self.declare_parameter(
            "status_topic", "/reception/qr/status"
        ).value
        self.validation_url = self.declare_parameter(
            "validation_url", ""
        ).value
        self.request_timeout_sec = float(
            self.declare_parameter("request_timeout_sec", 3.0).value
        )
        self.duplicate_cooldown_sec = float(
            self.declare_parameter("duplicate_cooldown_sec", 5.0).value
        )
        self.validation_service = self.declare_parameter(
            "validation_service", "/reception/qr/validate"
        ).value
        self.enable_legacy_topic_bridge = bool(
            self.declare_parameter("enable_legacy_topic_bridge", False).value
        )
        self.mock_mode = bool(
            self.declare_parameter("mock_mode", True).value
        )
        self.validation_url = validate_backend_configuration(
            self.mock_mode,
            str(self.validation_url),
            self.request_timeout_sec,
            self.duplicate_cooldown_sec,
        )
        mock_outcome_value = str(
            self.declare_parameter("mock_outcome", "valid").value
        ).strip().lower()
        self.mock_destination_id = str(
            self.declare_parameter("mock_destination_id", "mock-room").value
        ).strip()
        try:
            self.mock_outcome = QrValidationOutcome(mock_outcome_value)
        except ValueError as exc:
            raise ValueError(
                "'mock_outcome' must be valid, invalid, expired, duplicate, "
                "or unavailable"
            ) from exc

        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.create_service(
            ValidateQr, self.validation_service, self.on_validate_qr
        )
        if self.enable_legacy_topic_bridge:
            self.create_subscription(
                String, self.qr_detections_topic, self.on_qr_detection, 10
            )
        self.validation_executor = ThreadPoolExecutor(max_workers=1)
        self.in_flight = False
        self.last_payload = ""
        self.last_payload_at = 0.0

        self.publish_status(
            "waiting",
            "Waiting for the robot camera...",
        )
        self.get_logger().info(
            f"QR reservation bridge serving {self.validation_service}, "
            f"legacy_topic_bridge={self.enable_legacy_topic_bridge}, "
            f"mock_mode={self.mock_mode}, "
            f"backend={'mock' if self.mock_mode else 'configured-real'}"
        )

    def on_qr_detection(self, msg: String) -> None:
        decoded_text = extract_decoded_text(msg.data)
        if not decoded_text:
            self.publish_status(
                "error",
                "QR code could not be decoded.",
                error_code="invalid_qr",
            )
            return

        now = time.monotonic()
        if (
            decoded_text == self.last_payload
            and now - self.last_payload_at < self.duplicate_cooldown_sec
        ):
            return

        if self.in_flight:
            return

        self.in_flight = True
        self.last_payload = decoded_text
        self.last_payload_at = now
        self.publish_status("scanned", "QR detected.")
        self.publish_status("validating", "Validating your reservation...")
        self.validation_executor.submit(self.validate_qr_payload, decoded_text)

    def validate_qr_payload(self, qr_payload: str) -> None:
        result = self.perform_validation(qr_payload)
        self.publish_validation_status(result)
        self.in_flight = False

    def on_validate_qr(
        self,
        request: ValidateQr.Request,
        response: ValidateQr.Response,
    ) -> ValidateQr.Response:
        result = self.perform_validation(request.qr_payload)
        self.publish_validation_status(result)
        outcome_values = {
            QrValidationOutcome.VALID: ValidateQr.Response.VALID,
            QrValidationOutcome.INVALID: ValidateQr.Response.INVALID,
            QrValidationOutcome.EXPIRED: ValidateQr.Response.EXPIRED,
            QrValidationOutcome.DUPLICATE: ValidateQr.Response.DUPLICATE,
            QrValidationOutcome.UNAVAILABLE: ValidateQr.Response.UNAVAILABLE,
        }
        response.outcome = outcome_values[result.outcome]
        response.request_id = request.request_id
        response.destination_id = result.destination_id
        response.message = result.message
        return response

    def perform_validation(self, qr_payload: str) -> BridgeValidation:
        if not qr_payload.strip():
            return BridgeValidation(
                QrValidationOutcome.INVALID,
                "QR code could not be decoded.",
                error_code="invalid_qr",
            )
        if self.mock_mode:
            destination_id = (
                self.mock_destination_id
                if self.mock_outcome == QrValidationOutcome.VALID
                else ""
            )
            return BridgeValidation(
                self.mock_outcome,
                f"Mock QR validation outcome: {self.mock_outcome.value}.",
                destination_id=destination_id,
                error_code=(
                    None
                    if self.mock_outcome == QrValidationOutcome.VALID
                    else self.mock_outcome.value
                ),
            )

        try:
            api_response = self.post_json(
                self.validation_url, {"qr_payload": qr_payload}
            )
            body = api_response.get("body", {})
            data = successful_validation_data(body)
            if data is None:
                return BridgeValidation(
                    QrValidationOutcome.UNAVAILABLE,
                    "Reservation service returned an invalid response.",
                    error_code="malformed_response",
                )
            reservation = self.reservation_from_response(data)
            destination_id = self.destination_id_from_response(body, data)
            if not destination_id:
                return BridgeValidation(
                    QrValidationOutcome.UNAVAILABLE,
                    "Validated reservation has no stable destination ID.",
                    reservation=reservation,
                    error_code="missing_destination",
                )
            self.get_logger().info("Reservation QR validated")
            return BridgeValidation(
                QrValidationOutcome.VALID,
                body.get("message", "Reservation validated."),
                destination_id=destination_id,
                reservation=reservation,
            )
        except HTTPError as exc:
            body = self.read_error_body(exc)
            error_code = self.error_code_from_response(exc.code, body)
            message = self.message_from_response(body, exc.code)
            reservation = body.get("data", {}) if isinstance(body, dict) else {}
            outcome = outcome_from_error_code(error_code)
            self.get_logger().warning(f"Reservation QR rejected: {message}")
            return BridgeValidation(
                outcome,
                message,
                reservation=self.reservation_from_response(reservation),
                error_code=error_code,
            )
        except (TimeoutError, URLError, OSError) as exc:
            self.get_logger().warning(f"Reservation API unreachable: {exc}")
            return BridgeValidation(
                QrValidationOutcome.UNAVAILABLE,
                "Reservation service is unreachable.",
                error_code="api_unreachable",
            )
        except Exception as exc:
            self.get_logger().warning(f"Reservation validation failed: {exc}")
            return BridgeValidation(
                QrValidationOutcome.UNAVAILABLE,
                "Reservation validation failed.",
                error_code="api_unreachable",
            )

    def publish_validation_status(self, result: BridgeValidation) -> None:
        self.publish_status(
            "success" if result.outcome == QrValidationOutcome.VALID else "error",
            result.message,
            reservation=result.reservation,
            error_code=result.error_code,
        )

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.request_timeout_sec) as response:
            body = response.read().decode("utf-8")
            return {
                "status": response.status,
                "body": json.loads(body) if body else {},
            }

    @staticmethod
    def read_error_body(exc: HTTPError) -> dict[str, Any]:
        try:
            body = exc.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def error_code_from_response(status_code: int, body: dict[str, Any]) -> str:
        if isinstance(body.get("error_code"), str):
            return body["error_code"]
        if status_code in (400, 404, 422):
            return "invalid_qr"
        return "api_unreachable"

    @staticmethod
    def destination_id_from_response(body: Any, data: Any) -> str:
        candidates = []
        if isinstance(body, dict):
            candidates.append(body.get("destination_id"))
        if isinstance(data, dict):
            candidates.extend((data.get("destination_id"), data.get("room_id")))
        for value in candidates:
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                destination_id = str(value).strip()
                if destination_id:
                    return destination_id
        return ""

    @staticmethod
    def message_from_response(body: dict[str, Any], status_code: int) -> str:
        if isinstance(body.get("message"), str):
            return body["message"]
        status_label = responses.get(status_code, "Validation error")
        return f"Reservation validation failed: {status_label}."

    @staticmethod
    def reservation_from_response(data: Any) -> Optional[dict[str, Any]]:
        if not isinstance(data, dict):
            return None

        return {
            "uuid": data.get("uuid"),
            "customer_name": data.get("customer_name"),
            "room_id": data.get("room_id"),
            "room": data.get("room"),
            "date": data.get("date"),
            "start_at": data.get("start_at"),
            "end_at": data.get("end_at"),
        }

    def publish_status(
        self,
        state: str,
        message: str,
        reservation: Optional[dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        msg = String()
        msg.data = json.dumps(
            {
                "state": state,
                "message": message,
                "reservation": reservation,
                "error_code": error_code,
                "source": "robot_camera",
            },
            separators=(",", ":"),
        )
        self.status_pub.publish(msg)

    def destroy_node(self) -> bool:
        self.validation_executor.shutdown(wait=False, cancel_futures=True)
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node: QrReservationBridgeNode | None = None
    try:
        node = QrReservationBridgeNode()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("qr_reservation_bridge_node").fatal(str(exc))
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
