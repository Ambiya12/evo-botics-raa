#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.client import responses
import json
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


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
            "validation_url", "http://127.0.0.1:8000/api/reservations/validate"
        ).value
        self.request_timeout_sec = float(
            self.declare_parameter("request_timeout_sec", 3.0).value
        )
        self.duplicate_cooldown_sec = float(
            self.declare_parameter("duplicate_cooldown_sec", 5.0).value
        )

        self.status_pub = self.create_publisher(String, self.status_topic, 10)
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
            f"QR reservation bridge listening on {self.qr_detections_topic}, "
            f"publishing {self.status_topic}, validating with {self.validation_url}"
        )

    def on_qr_detection(self, msg: String) -> None:
        decoded_text = self.extract_decoded_text(msg.data)
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

    @staticmethod
    def extract_decoded_text(raw_data: str) -> Optional[str]:
        try:
            event = json.loads(raw_data)
        except json.JSONDecodeError:
            return raw_data if raw_data.strip() else None

        if isinstance(event, dict) and isinstance(event.get("decoded_text"), str):
            return event["decoded_text"]
        return None

    def validate_qr_payload(self, qr_payload: str) -> None:
        try:
            response = self.post_json(self.validation_url, {"qr_payload": qr_payload})
            body = response.get("body", {})
            data = body.get("data", {}) if isinstance(body, dict) else {}
            self.publish_status(
                "success",
                body.get("message", "Reservation validated."),
                reservation=self.reservation_from_response(data),
            )
            self.get_logger().info("Reservation QR validated")
        except HTTPError as exc:
            body = self.read_error_body(exc)
            error_code = self.error_code_from_response(exc.code, body)
            message = self.message_from_response(body, exc.code)
            reservation = body.get("data", {}) if isinstance(body, dict) else {}
            self.publish_status(
                "error",
                message,
                reservation=self.reservation_from_response(reservation),
                error_code=error_code,
            )
            self.get_logger().warning(f"Reservation QR rejected: {message}")
        except (TimeoutError, URLError, OSError) as exc:
            self.publish_status(
                "error",
                "Reservation service is unreachable.",
                error_code="api_unreachable",
            )
            self.get_logger().warning(f"Reservation API unreachable: {exc}")
        except Exception as exc:
            self.publish_status(
                "error",
                "Reservation validation failed.",
                error_code="api_unreachable",
            )
            self.get_logger().warning(f"Reservation validation failed: {exc}")
        finally:
            self.in_flight = False

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
    node = QrReservationBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
