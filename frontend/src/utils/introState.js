/**
 * In-memory module-level state for the one-time Sky Reader intro animation.
 *
 * Rules:
 * - Plays once per page load while signed out.
 * - Switching between /login and /signup, re-renders, and failed auth attempts do NOT replay it.
 * - A browser refresh (re-executing modules) resets it.
 */

let introPlayed = false;

export function hasIntroPlayed() {
  return introPlayed;
}

export function markIntroPlayed() {
  introPlayed = true;
}

export function resetIntroStateForTesting() {
  introPlayed = false;
}
