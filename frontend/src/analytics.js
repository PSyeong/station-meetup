import ReactGA from "react-ga4";

const DEFAULT_MEASUREMENT_ID = "G-BSR7CB0XJM";
const MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID || DEFAULT_MEASUREMENT_ID;

let initialized = false;

export function initAnalytics() {
  if (!MEASUREMENT_ID || initialized) return;
  ReactGA.initialize(MEASUREMENT_ID);
  initialized = true;
}

export function trackEvent(name, params) {
  if (!initialized) return;
  ReactGA.event(name, params);
}
