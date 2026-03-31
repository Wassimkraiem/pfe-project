"use client";

import { useEffect, useRef, useCallback } from "react";

/**
 * Hook to show a browser confirmation dialog when the user tries to:
 * - Refresh the page
 * - Close the tab/window
 * - Navigate to a different URL
 *
 * @param enabled - Whether the warning should be active (default: true)
 * @param message - Custom message (note: most browsers ignore custom messages for security)
 * @returns A function to imperatively disable the warning (useful before programmatic navigation)
 */
export function useBeforeUnload(enabled: boolean = true, message?: string) {
  const enabledRef = useRef(enabled);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const disable = useCallback(() => {
    enabledRef.current = false;
  }, []);

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!enabledRef.current) return;
      event.preventDefault();
      if (message) {
        event.returnValue = message;
      }
      return message || "";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [message]);

  return disable;
}

export default useBeforeUnload;
