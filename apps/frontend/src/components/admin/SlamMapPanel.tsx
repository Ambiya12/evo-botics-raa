import { useEffect, useRef, useState } from "react";
import { Panel } from "../ui/Panel";

const COLS = 40;
const ROWS = 40;
const ROBOT_X = 20;
const ROBOT_Y = 20;

function generateMockMap(cols: number, rows: number): Int8Array {
  const data = new Int8Array(cols * rows).fill(0); // tout libre
  // bord extérieur = obstacles
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) {
        data[r * cols + c] = 100;
      }
    }
  }
  // Quelques obstacles internes (murs)
  for (let c = 5; c < 15; c++) data[10 * cols + c] = 100; // mur horizontal
  for (let r = 20; r < 35; r++) data[r * cols + 25] = 100; // mur vertical
  for (let c = 28; c < 38; c++) data[15 * cols + c] = 100; // autre mur
  return data;
}

function drawMap(
  ctx: CanvasRenderingContext2D,
  data: Int8Array,
  cols: number,
  rows: number,
  robotX: number,
  robotY: number,
  offsetX: number,
  offsetY: number,
  scale: number,
): void {
  const cellSize = scale; // pixels par cellule
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  // fond
  ctx.fillStyle = "#e8e4dd";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const val = data[r * cols + c];
      if (val === 100) ctx.fillStyle = "#2d2d2d"; // obstacle
      else if (val === -1) ctx.fillStyle = "#aaa9a5"; // inconnu
      else ctx.fillStyle = "#f5f3ef"; // libre
      ctx.fillRect(
        offsetX + c * cellSize,
        offsetY + r * cellSize,
        cellSize - 0.5,
        cellSize - 0.5,
      );
    }
  }

  // Robot : cercle bleu centré sur (robotX, robotY)
  const rx = offsetX + robotX * cellSize + cellSize / 2;
  const ry = offsetY + robotY * cellSize + cellSize / 2;

  ctx.beginPath();
  ctx.arc(rx, ry, cellSize * 1.2, 0, Math.PI * 2);
  ctx.fillStyle = "#3b82f6";
  ctx.fill();

  ctx.beginPath();
  ctx.arc(rx, ry, cellSize * 1.2, 0, Math.PI * 2);
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

export function SlamMapPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scale, setScale] = useState(10); // px par cellule
  const [offset, setOffset] = useState({ x: 20, y: 20 });
  const isDragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const mapData = useRef(generateMockMap(COLS, ROWS));

  // Draw whenever scale or offset changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    drawMap(ctx, mapData.current, COLS, ROWS, ROBOT_X, ROBOT_Y, offset.x, offset.y, scale);
  }, [scale, offset]);

  // Native wheel listener with { passive: false } to allow preventDefault
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function handleWheel(e: WheelEvent): void {
      e.preventDefault();
      setScale((prev) => {
        const delta = e.deltaY > 0 ? -1 : 1;
        return Math.min(24, Math.max(4, prev + delta));
      });
    }

    canvas.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      canvas.removeEventListener("wheel", handleWheel);
    };
  }, []);

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>): void {
    isDragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  }

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!isDragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current = { x: e.clientX, y: e.clientY };
    setOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
  }

  function handleMouseUp(): void {
    isDragging.current = false;
  }

  function handleMouseLeave(): void {
    isDragging.current = false;
  }

  return (
    <Panel eyebrow="Navigation" title="SLAM Map" className="slam-panel">
      <div className="slam-canvas-wrap">
        <canvas
          ref={canvasRef}
          width={480}
          height={360}
          className="slam-canvas"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
        <p className="slam-hint">Mock map — drag to pan · scroll to zoom</p>
      </div>
    </Panel>
  );
}
