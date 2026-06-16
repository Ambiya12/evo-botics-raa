import { useEffect, useRef, useState } from 'react';
import type { NavPath, OccupancyGrid, RobotPose } from './types';

type Props = {
    map: OccupancyGrid | null;
    path: NavPath | null;
    pose: RobotPose | null;
    onGoal?: (x: number, y: number) => void;
};

type Viewport = {
    height: number;
    offsetX: number;
    offsetY: number;
    scale: number;
    width: number;
};

export default function MapCanvas({ map, onGoal, path, pose }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const wrapperRef = useRef<HTMLDivElement>(null);
    const viewportRef = useRef<Viewport | null>(null);
    const [selectedPoint, setSelectedPoint] = useState<{ x: number; y: number } | null>(null);
    const [sizeVersion, setSizeVersion] = useState(0);

    useEffect(() => {
        const wrapper = wrapperRef.current;
        if (!wrapper) return;

        const observer = new ResizeObserver(() => {
            setSizeVersion((version) => version + 1);
        });
        observer.observe(wrapper);

        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        drawMap();
    }, [map, path, pose, selectedPoint, sizeVersion]);

    const mapToCanvas = (x: number, y: number, viewport: Viewport) => {
        if (!map) return null;
        const { height, origin, resolution } = {
            height: map.info.height,
            origin: map.info.origin.position,
            resolution: map.info.resolution,
        };
        const gridX = (x - origin.x) / resolution;
        const gridY = height - (y - origin.y) / resolution;

        return {
            x: viewport.offsetX + gridX * viewport.scale,
            y: viewport.offsetY + gridY * viewport.scale,
        };
    };

    const drawMap = () => {
        const canvas = canvasRef.current;
        const wrapper = wrapperRef.current;
        if (!canvas || !wrapper) return;

        const dpr = window.devicePixelRatio || 1;
        const bounds = wrapper.getBoundingClientRect();
        canvas.width = Math.max(1, Math.floor(bounds.width * dpr));
        canvas.height = Math.max(1, Math.floor(bounds.height * dpr));
        canvas.style.width = `${bounds.width}px`;
        canvas.style.height = `${bounds.height}px`;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, bounds.width, bounds.height);
        ctx.fillStyle = '#111827';
        ctx.fillRect(0, 0, bounds.width, bounds.height);

        if (!map) {
            ctx.fillStyle = '#9ca3af';
            ctx.font = '14px system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Waiting for /map', bounds.width / 2, bounds.height / 2);
            ctx.font = '12px system-ui, sans-serif';
            ctx.fillText('Start Nav2 or map_server with a map inside the Docker container.', bounds.width / 2, bounds.height / 2 + 24);
            return;
        }

        const { width, height, resolution, origin } = map.info;
        const scale = Math.min(bounds.width / width, bounds.height / height);
        const mapPixelWidth = width * scale;
        const mapPixelHeight = height * scale;
        const offsetX = (bounds.width - mapPixelWidth) / 2;
        const offsetY = (bounds.height - mapPixelHeight) / 2;
        const viewport = { height, offsetX, offsetY, scale, width };
        viewportRef.current = viewport;

        const imageCanvas = document.createElement('canvas');
        imageCanvas.width = width;
        imageCanvas.height = height;
        const imageCtx = imageCanvas.getContext('2d');
        if (!imageCtx) return;

        const imageData = imageCtx.createImageData(width, height);
        for (let i = 0; i < map.data.length; i += 1) {
            const value = map.data[i];
            const x = i % width;
            const y = height - 1 - Math.floor(i / width);
            const index = (y * width + x) * 4;
            const color = value < 0 ? 72 : value < 35 ? 241 : 31;
            const obstacle = value >= 35;

            imageData.data[index] = obstacle ? 31 : color;
            imageData.data[index + 1] = obstacle ? 41 : color;
            imageData.data[index + 2] = obstacle ? 55 : color;
            imageData.data[index + 3] = value < 0 ? 190 : 255;
        }
        imageCtx.putImageData(imageData, 0, 0);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(imageCanvas, offsetX, offsetY, mapPixelWidth, mapPixelHeight);

        ctx.strokeStyle = 'rgba(59, 130, 246, 0.35)';
        ctx.strokeRect(offsetX, offsetY, mapPixelWidth, mapPixelHeight);

        if (path?.poses && path.poses.length > 1) {
            ctx.beginPath();
            path.poses.forEach((item, index) => {
                const point = mapToCanvas(item.pose.position.x, item.pose.position.y, viewport);
                if (!point) return;
                if (index === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
            ctx.strokeStyle = '#2563eb';
            ctx.lineWidth = 3;
            ctx.stroke();
        }

        if (selectedPoint) {
            const point = mapToCanvas(selectedPoint.x, selectedPoint.y, viewport);
            if (point) {
                ctx.fillStyle = '#f59e0b';
                ctx.beginPath();
                ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }

        if (pose) {
            const point = mapToCanvas(pose.x, pose.y, viewport);
            if (point) {
                ctx.save();
                ctx.translate(point.x, point.y);
                ctx.rotate(-pose.yaw);
                ctx.fillStyle = '#059669';
                ctx.beginPath();
                ctx.moveTo(12, 0);
                ctx.lineTo(-8, -7);
                ctx.lineTo(-5, 0);
                ctx.lineTo(-8, 7);
                ctx.closePath();
                ctx.fill();
                ctx.restore();
            }
        }

        ctx.fillStyle = '#111827';
        ctx.font = '12px system-ui, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`${width} x ${height} @ ${resolution.toFixed(2)}m`, offsetX + 10, offsetY + 20);
        ctx.fillText(`origin ${origin.position.x.toFixed(2)}, ${origin.position.y.toFixed(2)}`, offsetX + 10, offsetY + 38);
    };

    const handleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!onGoal || !map || !viewportRef.current || !canvasRef.current) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const viewport = viewportRef.current;
        const canvasX = event.clientX - rect.left;
        const canvasY = event.clientY - rect.top;
        const gridX = (canvasX - viewport.offsetX) / viewport.scale;
        const gridYFromTop = (canvasY - viewport.offsetY) / viewport.scale;

        if (gridX < 0 || gridYFromTop < 0 || gridX > map.info.width || gridYFromTop > map.info.height) {
            return;
        }

        const x = map.info.origin.position.x + gridX * map.info.resolution;
        const y = map.info.origin.position.y + (map.info.height - gridYFromTop) * map.info.resolution;
        const point = { x, y };
        setSelectedPoint(point);
        onGoal(x, y);
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Map & Navigation</h3>
                    <p className="text-xs text-gray-500">{onGoal ? 'Click the map to send a Nav2 goal' : 'Live map (read-only)'}</p>
                </div>
                {selectedPoint && (
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                        Goal {selectedPoint.x.toFixed(2)}, {selectedPoint.y.toFixed(2)}
                    </span>
                )}
            </div>
            <div className="h-[520px] min-h-[360px] bg-gray-950" ref={wrapperRef}>
                <canvas className={onGoal ? 'block cursor-crosshair' : 'block'} onClick={handleClick} ref={canvasRef} />
            </div>
        </section>
    );
}
