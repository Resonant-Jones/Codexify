import { forwardRef } from "react";
import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

type SettingsRangeControlProps = Omit<
  ComponentPropsWithoutRef<"input">,
  "type"
> & {
  /** Optional className for the wrapper element. */
  className?: string;
};

const SettingsRangeControl = forwardRef<
  HTMLInputElement,
  SettingsRangeControlProps
>(function SettingsRangeControl({ className, ...rest }, ref) {
  return (
    <div className={cn("w-full", className)}>
      <input
        ref={ref}
        type="range"
        className="w-full"
        style={{ accentColor: "var(--accent)" }}
        {...rest}
      />
    </div>
  );
});

export default SettingsRangeControl;
