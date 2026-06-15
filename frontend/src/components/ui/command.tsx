"use client";

import * as React from "react";
import { Command as CommandPrimitive } from "cmdk";
import { Dialog } from "radix-ui";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

const Command = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive>
>(({ className, ...props }, ref) => (
  <CommandPrimitive
    ref={ref}
    className={cn("flex h-full w-full flex-col overflow-hidden", className)}
    {...props}
  />
));
Command.displayName = "Command";

/** Command palette rendered inside a centered dialog. */
function CommandDialog({
  open,
  onOpenChange,
  label = "Command menu",
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-canvas/80 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-[18%] z-50 w-full max-w-xl -translate-x-1/2",
            "overflow-hidden rounded-xl border border-hairline-strong bg-surface-2 shadow-2xl",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          )}
        >
          <Dialog.Title className="sr-only">{label}</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search for an action or destination, then press Enter.
          </Dialog.Description>
          <Command className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[0.6875rem] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.06em] [&_[cmdk-group-heading]]:text-ink-faint">
            {children}
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const CommandInput = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Input>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Input>
>(({ className, ...props }, ref) => (
  <div className="flex items-center gap-2 border-b border-hairline px-3" cmdk-input-wrapper="">
    <Search size={15} className="shrink-0 text-ink-subtle" aria-hidden="true" />
    <CommandPrimitive.Input
      ref={ref}
      className={cn(
        "flex h-11 w-full bg-transparent py-3 text-sm text-ink outline-none placeholder:text-ink-faint disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  </div>
));
CommandInput.displayName = "CommandInput";

const CommandList = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.List>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.List
    ref={ref}
    className={cn("max-h-80 overflow-y-auto overflow-x-hidden p-1.5", className)}
    {...props}
  />
));
CommandList.displayName = "CommandList";

const CommandEmpty = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Empty>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Empty>
>((props, ref) => (
  <CommandPrimitive.Empty
    ref={ref}
    className="py-8 text-center text-sm text-ink-subtle"
    {...props}
  />
));
CommandEmpty.displayName = "CommandEmpty";

const CommandGroup = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Group>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Group>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Group
    ref={ref}
    className={cn("overflow-hidden text-ink", className)}
    {...props}
  />
));
CommandGroup.displayName = "CommandGroup";

const CommandItem = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Item>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Item
    ref={ref}
    className={cn(
      "flex cursor-pointer select-none items-center gap-2.5 rounded-md px-3 py-2 text-sm text-ink-muted outline-none",
      "data-[selected=true]:bg-surface-3 data-[selected=true]:text-ink",
      "data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50",
      "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-ink-subtle data-[selected=true]:[&_svg]:text-lav-hi",
      className,
    )}
    {...props}
  />
));
CommandItem.displayName = "CommandItem";

function CommandShortcut({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "ml-auto font-mono text-[0.6875rem] tracking-widest text-ink-faint",
        className,
      )}
      {...props}
    />
  );
}

export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
};
