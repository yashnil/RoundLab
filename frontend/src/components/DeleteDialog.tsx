"use client";

import { Button } from "@/components/ui/button";
import {
  DialogRoot, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { AlertTriangle } from "lucide-react";

interface DeleteDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  isDeleting?: boolean;
  error?: string;
}

export default function DeleteDialog({
  open, onOpenChange, title, description, onConfirm, isDeleting = false, error,
}: DeleteDialogProps) {
  return (
    <DialogRoot open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg border border-danger/20 bg-danger/10">
            <AlertTriangle size={15} className="text-danger" />
          </div>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {error && (
          <div className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
            {error}
          </div>
        )}
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => onOpenChange(false)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={onConfirm}
            disabled={isDeleting}
            className="bg-danger text-white hover:bg-danger/90 focus-visible:ring-danger/40"
          >
            {isDeleting ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
