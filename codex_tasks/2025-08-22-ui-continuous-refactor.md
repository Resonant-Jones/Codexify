# ----  Codex CLI prompt  -----------------------------------------------------

codex patch --apply <<'PATCH'

# Goal: Give each stubbed UI primitive (button, card, input, etc.) a sensible

# default Tailwind style, while still letting callers extend via className

# No runtime behavior should change – only visuals / classNames

#

# Important constraints

# • Keep the existing forwardRef + props shapes exactly as-is

# • Continue to spread {...props} so external props/aria/data-* still work

# • Accept a `className` prop that MERGES (not overrides) with the baseline

# classes (use clsx() – already imported – or create one if missing)

# • Support the small set of variants already referenced in code

# - Button:   variant = "default" | "ghost" | "destructive"

# - Button:   size    = "sm" | "md" (default) | "lg"  (optional, but wire)

#

# • Use design tokens already defined in src/index.css

# --panel-bg, --panel-border, --accent, --accent-weak, --accent-strong

# --text, --chip-bg

# • No additional packages – Tailwind only

#

# Files to create/modify

# src/components/ui/button.tsx

# src/components/ui/card.tsx

# src/components/ui/input.tsx

# src/components/ui/textarea.tsx

# src/components/ui/separator.tsx

# src/components/ui/badge.tsx

# src/components/ui/avatar.tsx

#

# ---------------------------------------------------------------------------

@@ src/components/ui/button.tsx
-/*existing stub*/
+import * as React from "react";
+import { clsx } from "clsx";
+
+export type Variant = "default" | "ghost" | "destructive";
+export type Size = "sm" | "md" | "lg";
+
+export interface ButtonProps

+ extends React.ButtonHTMLAttributes<HTMLButtonElement> {
+ variant?: Variant;
+ size?: Size;
+}
+

+export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(

+ ({ variant = "default", size = "md", className, ...props }, ref) => {
+ const base =
+      "inline-flex items-center justify-center font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none rounded-xl";
+ const variantClasses = {
+      default:
+        "bg-[--accent] text-[--panel-bg] hover:bg-[--accent-strong] focus-visible:ring-2 focus-visible:ring-[--accent-strong]",
+      ghost:
+        "bg-transparent hover:bg-[--accent-weak]/20 text-[--text] focus-visible:ring-2 focus-visible:ring-[--accent]",
+      destructive:
+        "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700",
+ }[variant];
+ const sizeClasses = {
+      sm: "h-7 px-3 text-xs",
+      md: "h-9 px-4 text-sm",
+      lg: "h-11 px-6 text-base",
+ }[size];
+
+ return (
+      <button
+        ref={ref}
+        className={clsx(base, variantClasses, sizeClasses, className)}
+        {...props}
+      />
+ );
+ }
+);
+Button.displayName = "Button";

@@ src/components/ui/card.tsx
-/*existing stub*/
+import * as React from "react";
+import { clsx } from "clsx";
+
+export interface CardProps

+ extends React.HTMLAttributes<HTMLDivElement> {}
+

+export const Card = React.forwardRef<HTMLDivElement, CardProps>(

+ ({ className, ...props }, ref) => (
+ <div
+      ref={ref}
+      className={clsx(
+        "rounded-2xl border border-[--panel-border] bg-[--panel-bg]/60 backdrop-blur-md",
+        className
+      )}
+      {...props}
+ />
+ )
+);
+Card.displayName = "Card";

@@ src/components/ui/input.tsx
+import * as React from "react";
+import { clsx } from "clsx";
+
+export interface InputProps

+ extends React.InputHTMLAttributes<HTMLInputElement> {}
+

+export const Input = React.forwardRef<HTMLInputElement, InputProps>(

+ ({ className, ...props }, ref) => (
+ <input
+      ref={ref}
+      className={clsx(
+        "w-full h-9 rounded-md border border-[--panel-border] bg-[--panel-bg]/80 px-3 py-1 text-sm text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--accent]",
+        className
+      )}
+      {...props}
+ />
+ )
+);
+Input.displayName = "Input";

@@ src/components/ui/textarea.tsx
+/*similar to Input but textarea*/
+import * as React from "react";
+import { clsx } from "clsx";
+
+export interface TextareaProps

+ extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}
+

+export const Textarea = React.forwardRef<

+ HTMLTextAreaElement,
+ TextareaProps
+>(({ className, ...props }, ref) => (
+ <textarea
+ ref={ref}
+ className={clsx(
+      "w-full rounded-md border border-[--panel-border] bg-[--panel-bg]/80 px-3 py-2 text-sm text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--accent] resize-none",
+      className
+ )}
+ {...props}
+ />
+));
+Textarea.displayName = "Textarea";

@@ src/components/ui/separator.tsx
+export const Separator = ({ className = "" }: { className?: string }) => (

+ <hr className={clsx("border-t border-[--panel-border]", className)} />

+);

@@ src/components/ui/badge.tsx
+import { clsx } from "clsx";
+export const Badge = ({

+ children,
+ className,
+}: React.HTMLAttributes<HTMLSpanElement>) => (
+ <span
+ className={clsx(
+      "inline-block rounded-full bg-[--accent-weak]/40 px-2 py-0.5 text-xs font-medium text-[--text]",
+      className
+ )}
+ >
+ {children}
+ </span>

+);

@@ src/components/ui/avatar.tsx
+import * as React from "react";
+import { clsx } from "clsx";
+
+export interface AvatarProps

+ extends React.ImgHTMLAttributes<HTMLImageElement> {}
+

+export const Avatar = React.forwardRef<HTMLImageElement, AvatarProps>(

+ ({ className, ...props }, ref) => (
+ <img
+      ref={ref}
+      className={clsx("h-8 w-8 rounded-full object-cover", className)}
+      {...props}
+ />
+ )
+);
+Avatar.displayName = "Avatar";

# Remove @ts-expect-error line in the test (unused after refactor)

@@ src/components/ui/__tests__/refractive-glass-card.guard.test.tsx
+ // @ts-expect-error test override
 PATCH

# ------------------------------------------------------------------------------
