"use client";

import { motion, useReducedMotion } from "motion/react";

type OrbProps = {
  /** Loudness 0–1. Driven by a demo now; by the player's Web Audio analyser later. */
  level?: number;
  className?: string;
};

// The "voice": a tungsten orb that swells with the speech and breathes when idle.
export function Orb({ level = 0, className = "" }: OrbProps) {
  const reduce = useReducedMotion();

  return (
    <div aria-hidden className={`relative aspect-square ${className}`}>
      {/* Outer layer reacts to loudness with a spring, so it feels physical */}
      <motion.div
        className="absolute inset-0"
        animate={{ scale: 1 + level * 0.07 }}
        transition={{ type: "spring", stiffness: 180, damping: 18 }}
      >
        <motion.div
          className="absolute inset-0 rounded-full bg-[radial-gradient(circle,rgb(255_181_71/0.45),transparent_62%)] blur-2xl"
          animate={{ opacity: 0.55 + level * 0.45 }}
          transition={{ duration: 0.25 }}
        />
        {/* Inner core breathes slowly when nothing is playing */}
        <motion.div
          className="absolute inset-[20%] rounded-full bg-[radial-gradient(circle_at_35%_28%,#fff1d6,#ffb547_32%,#b5561f_68%,#2a120a)] shadow-[inset_0_-24px_60px_rgb(0_0_0/0.55),0_0_80px_rgb(255_181_71/0.25)]"
          animate={reduce ? undefined : { scale: [1, 1.025, 1] }}
          transition={{ duration: 5, repeat: Infinity, ease: [0.37, 0, 0.63, 1] }}
        />
      </motion.div>
    </div>
  );
}
