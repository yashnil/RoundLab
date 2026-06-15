"use client";

import * as React from "react";
import { Dialog } from "radix-ui";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const SheetRoot = Dialog.Root;
const SheetTrigger = Dialog.Trigger;
const SheetClose = Dialog.Close;
const SheetPortal = Dialog.Portal;

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof Dialog.Overlay>,
  React.ComponentPropsWithoutRef<typeof Dialog.Overlay>
>(({ className, ...props }, ref) => (
  <Dialog.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-canvas/80 backdrop-blur-[2px]",
      "data-[state=open]:animate-in data-[state=closed]:animate-out",
      "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className,
    )}
    {...props}
  />
));
SheetOverlay.displayName = "SheetOverlay";

type Side = "left" | "right" | "top" | "bottom";

const sideClasses: Record<Side, string> = {
  left: "inset-y-0 left-0 h-full w-80 max-w-[85vw] border-r data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left",
  right:
    "inset-y-0 right-0 h-full w-80 max-w-[85vw] border-l data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right",
  top: "inset-x-0 top-0 w-full border-b data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top",
  bottom:
    "inset-x-0 bottom-0 w-full border-t data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom",
};

interface SheetContentProps
  extends React.ComponentPropsWithoutRef<typeof Dialog.Content> {
  side?: Side;
}

const SheetContent = React.forwardRef<
  React.ElementRef<typeof Dialog.Content>,
  SheetContentProps
>(({ className, children, side = "left", ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <Dialog.Content
      ref={ref}
      className={cn(
        "fixed z-50 flex flex-col gap-0 border-hairline-strong bg-sidebar shadow-2xl",
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[state=closed]:duration-200 data-[state=open]:duration-250",
        sideClasses[side],
        className,
      )}
      {...props}
    >
      {children}
      <Dialog.Close className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-3 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50">
        <X size={15} />
        <span className="sr-only">Close</span>
      </Dialog.Close>
    </Dialog.Content>
  </SheetPortal>
));
SheetContent.displayName = "SheetContent";

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof Dialog.Title>,
  React.ComponentPropsWithoutRef<typeof Dialog.Title>
>(({ className, ...props }, ref) => (
  <Dialog.Title
    ref={ref}
    className={cn("text-sm font-semibold tracking-tight text-ink", className)}
    {...props}
  />
));
SheetTitle.displayName = "SheetTitle";

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof Dialog.Description>,
  React.ComponentPropsWithoutRef<typeof Dialog.Description>
>(({ className, ...props }, ref) => (
  <Dialog.Description
    ref={ref}
    className={cn("text-xs leading-relaxed text-ink-subtle", className)}
    {...props}
  />
));
SheetDescription.displayName = "SheetDescription";

export {
  SheetRoot,
  SheetTrigger,
  SheetClose,
  SheetPortal,
  SheetOverlay,
  SheetContent,
  SheetTitle,
  SheetDescription,
};
