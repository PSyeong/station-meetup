// crypto.randomUUID()는 보안 컨텍스트(HTTPS 또는 localhost)에서만 쓸 수 있어서,
// LAN IP로 접속하는 일반 HTTP 환경(같은 와이파이의 다른 기기로 확인할 때 등)에서는 없다.
export function generateId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}
