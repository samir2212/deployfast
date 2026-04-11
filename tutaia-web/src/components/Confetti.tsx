import { useEffect, useState } from "react";

const COLORS = ["#8b5cf6", "#a78bfa", "#c4b5fd", "#6d28d9", "#f472b6", "#38bdf8", "#34d399"];

interface Piece {
  id: number;
  left: number;
  color: string;
  delay: number;
  size: number;
}

export default function Confetti() {
  const [pieces, setPieces] = useState<Piece[]>([]);

  useEffect(() => {
    const items: Piece[] = Array.from({ length: 60 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      delay: Math.random() * 2,
      size: Math.random() * 8 + 4,
    }));
    setPieces(items);

    const timer = setTimeout(() => setPieces([]), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {pieces.map((p) => (
        <div
          key={p.id}
          className="confetti-piece"
          style={{
            left: `${p.left}%`,
            backgroundColor: p.color,
            width: p.size,
            height: p.size * 1.5,
            animationDelay: `${p.delay}s`,
            borderRadius: "2px",
          }}
        />
      ))}
    </>
  );
}
