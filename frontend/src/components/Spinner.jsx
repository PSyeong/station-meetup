export default function Spinner({ size = 20, light = false }) {
  return (
    <span
      className={"spinner" + (light ? " spinner--light" : "")}
      style={{ width: size, height: size, borderWidth: Math.max(2, size / 8) }}
      role="status"
      aria-label="불러오는 중"
    />
  );
}
