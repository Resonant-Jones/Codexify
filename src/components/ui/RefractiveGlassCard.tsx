import React, { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  children: React.ReactNode;
  wallpaperUrl: string | null;
  radius?: number;
  intensity?: number;
  aberration?: number;
  className?: string;
  style?: React.CSSProperties;
};

function fallbackStyle(): React.CSSProperties {
  return {
    background:
      "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)",
    backdropFilter: "blur(12px) saturate(120%)",
    WebkitBackdropFilter: "blur(12px) saturate(120%)",
    borderColor: "rgba(255,255,255,0.18)",
    boxShadow:
      "inset 0 1px rgba(255,255,255,0.22), inset 0 -1px rgba(0,0,0,0.28), 0 10px 22px rgba(0,0,0,0.25)",
  };
}

export const RefractiveGlassCard: React.FC<Props> = ({
  children,
  wallpaperUrl,
  radius = 16,
  intensity = 0.012,
  aberration = 0.35,
  className,
  style,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  const img = useMemo(() => {
    if (!wallpaperUrl) return null;
    const i = new Image();
    i.crossOrigin = "anonymous";
    (i as any).decoding = "async";
    i.src = wallpaperUrl;
    return i;
  }, [wallpaperUrl]);

  useEffect(() => {
    if (!wallpaperUrl) { setFailed(true); return; }
    if (!img) return;
    const onload = () => setReady(true);
    const onerr = () => setFailed(true);
    img.addEventListener("load", onload);
    img.addEventListener("error", onerr);
    if ((img as any).complete && (img as any).naturalWidth) setReady(true);
    return () => {
      img.removeEventListener("load", onload);
      img.removeEventListener("error", onerr);
    };
  }, [img, wallpaperUrl]);

  useEffect(() => {
    if (!ready || failed) return;
    const canvas = canvasRef.current;
    const el = containerRef.current;
    if (!canvas || !el) { setFailed(true); return; }
    const gl = (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (!gl) { setFailed(true); return; }

    const vert = `#version 300 es\nprecision highp float;\nlayout(location=0) in vec2 position;\nout vec2 vUv;\nvoid main(){ vUv = position*0.5+0.5; gl_Position = vec4(position,0.0,1.0); }`;

    const frag = `#version 300 es\nprecision highp float;\nuniform sampler2D uTex;\nuniform vec2 uCanvasSize;\nuniform vec2 uWindowSize;\nuniform vec2 uImageSize;\nuniform vec2 uCoverSize;\nuniform vec2 uCoverOffset;\nuniform vec2 uCanvasTopLeft;\nuniform float uRadius;\nuniform float uIntensity;\nuniform float uAberration;\nin vec2 vUv;\nout vec4 outColor;\nfloat sdRoundRect(vec2 p, vec2 b, float r){ vec2 q = abs(p)-b+r; return length(max(q,0.0))+min(max(q.x,q.y),0.0)-r; }\nvec2 toWindow(vec2 uv){ return uCanvasTopLeft + uv * uCanvasSize; }\nvec2 windowToImage(vec2 wp){ vec2 p = (wp - uCoverOffset)/uCoverSize; return p; }\nvec3 sampleWP(vec2 uv){ return texture(uTex, uv).rgb; }\nvoid main(){ vec2 size = uCanvasSize; vec2 p = (vUv*size); vec2 halfSize = size*0.5; float r = uRadius; float sdf = sdRoundRect(p-halfSize, halfSize - vec2(1.0), r); float edge = smoothstep(2.0, 0.0, abs(sdf)); vec2 n = normalize(vec2(dFdx(sdf), dFdy(sdf)) + 1e-5); float k = clamp(1.0-abs(sdf)/r,0.0,1.0); float mag = uIntensity * k; vec2 wp = toWindow(vUv); vec2 baseUV = windowToImage(wp); vec2 offs = n * mag; vec3 col; col.r = sampleWP(baseUV + offs*uAberration).r; col.g = sampleWP(baseUV).g; col.b = sampleWP(baseUV - offs*uAberration).b; float bevelHi = smoothstep(-1.5, -0.5, -sdf); float bevelLo = smoothstep(-2.0, -0.5, sdf); col = mix(col, col*0.96, bevelLo*0.5); col += 0.06*bevelHi; outColor = vec4(col, edge*0.95); }`;

    function compileShader(ctx: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
      const s = ctx.createShader(type);
      if (!s) return null;
      ctx.shaderSource(s, src);
      ctx.compileShader(s);
      if (!ctx.getShaderParameter(s, ctx.COMPILE_STATUS)) return null;
      return s;
    }

    const vs = compileShader(gl, gl.VERTEX_SHADER, vert);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, frag);
    if (!vs || !fs) return;
    const prog = gl.createProgram();
    if (!prog) { setFailed(true); return; }
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.bindAttribLocation(prog, 0, "position");
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { setFailed(true); return; }

    const quad = gl.createBuffer();
    if (!quad) { setFailed(true); return; }
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);

    const tex = gl.createTexture();
    if (!tex) { setFailed(true); return; }
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    const uTex = gl.getUniformLocation(prog, "uTex");
    const uCanvasSize = gl.getUniformLocation(prog, "uCanvasSize");
    const uWindowSize = gl.getUniformLocation(prog, "uWindowSize");
    const uImageSize = gl.getUniformLocation(prog, "uImageSize");
    const uCoverSize = gl.getUniformLocation(prog, "uCoverSize");
    const uCoverOffset = gl.getUniformLocation(prog, "uCoverOffset");
    const uCanvasTopLeft = gl.getUniformLocation(prog, "uCanvasTopLeft");
    const uRadius = gl.getUniformLocation(prog, "uRadius");
    const uIntensity = gl.getUniformLocation(prog, "uIntensity");
    const uAberration = gl.getUniformLocation(prog, "uAberration");

    function coverSize(winW: number, winH: number, imgW: number, imgH: number) {
      const s = Math.max(winW / imgW, winH / imgH);
      return { w: imgW * s, h: imgH * s } as const;
    }

    function resize() {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const rect = el.getBoundingClientRect();
      canvas.width = Math.max(2, Math.round(rect.width * dpr));
      canvas.height = Math.max(2, Math.round(rect.height * dpr));
      canvas.style.width = `${Math.max(1, Math.round(rect.width))}px`;
      canvas.style.height = `${Math.max(1, Math.round(rect.height))}px`;
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function sync() {
      if (!img || !(img as any).width || !(img as any).height) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const rect = el.getBoundingClientRect();
      const winW = Math.round(window.innerWidth * dpr);
      const winH = Math.round(window.innerHeight * dpr);
      const topLeftX = Math.round((rect.left + window.scrollX) * dpr);
      const topLeftY = Math.round((rect.top + window.scrollY) * dpr);

      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      if (!(img as any)._bound) {
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img as any);
        (img as any)._bound = true;
      }

      const cov = coverSize(winW, winH, (img as any).naturalWidth || (img as any).width, (img as any).naturalHeight || (img as any).height);
      const offX = Math.round((winW - cov.w) / 2);
      const offY = Math.round((winH - cov.h) / 2);

      gl.uniform1i(uTex, 0);
      gl.uniform2f(uCanvasSize, canvas.width, canvas.height);
      gl.uniform2f(uWindowSize, winW, winH);
      gl.uniform2f(uImageSize, (img as any).width, (img as any).height);
      gl.uniform2f(uCoverSize, cov.w, cov.h);
      gl.uniform2f(uCoverOffset, offX, offY);
      gl.uniform2f(uCanvasTopLeft, topLeftX, topLeftY);
      gl.uniform1f(uRadius, radius * (window.devicePixelRatio || 1));
      gl.uniform1f(uIntensity, intensity);
      gl.uniform1f(uAberration, aberration);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    const ro = new ResizeObserver(() => { resize(); sync(); });
    resize();
    sync();
    ro.observe(el);
    const onScroll = () => sync();
    const onResize = () => { resize(); sync(); };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);

    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", onScroll as any);
      window.removeEventListener("resize", onResize as any);
    };
  }, [ready, failed, img, radius, intensity, aberration]);

  if (!wallpaperUrl || failed) {
    return (
      <div
        ref={containerRef}
        className={`rounded-2xl border shadow-xl overflow-hidden ${className || ""}`}
        style={{ ...fallbackStyle(), ...style }}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`relative rounded-2xl border overflow-hidden ${className || ""}`}
      style={{ borderColor: "rgba(255,255,255,0.18)", ...style }}
    >
      <canvas ref={canvasRef} className="absolute inset-0" />
      <div className="relative" style={{ boxShadow: "inset 0 1px rgba(255,255,255,0.22), inset 0 -1px rgba(0,0,0,0.28), 0 10px 22px rgba(0,0,0,0.25)" }}>
        {children}
      </div>
    </div>
  );
};

export default RefractiveGlassCard;
