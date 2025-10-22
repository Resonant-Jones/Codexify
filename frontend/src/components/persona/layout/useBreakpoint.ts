import { useEffect, useState } from "react";

type Breakpoint = "sm" | "md" | "lg" | "xl" | "2xl";

export function useBreakpoint(): Breakpoint {
  const get = () => {
    if (typeof window === "undefined") return "xl" as Breakpoint;
    const w = window.innerWidth;
    if (w < 768) return "sm";
    if (w < 1024) return "md";
    if (w < 1440) return "lg";
    if (w < 1920) return "xl";
    return "2xl";
  };

  const [bp, setBp] = useState<Breakpoint>(get);

  useEffect(() => {
    const on = () => setBp(get());
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);

  return bp;
}
