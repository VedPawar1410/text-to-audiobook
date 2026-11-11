"use client";

import { useEffect } from "react";

/** Registers public/sw.js, which serves saved books. Needs HTTPS (or localhost). */
export function ServiceWorker() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined);
    }
  }, []);
  return null;
}
