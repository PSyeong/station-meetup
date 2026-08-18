import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(__dirname, "..", "data");

// 담당1의 data/ 산출물(station_graph.json 등)을 별도 복사 없이 그대로 서빙한다.
// data/*.json이 새로 생성될 때마다 프론트가 항상 최신 상태를 보게 하려는 목적.
function serveProjectData() {
  return {
    name: "serve-project-data",
    configureServer(server) {
      server.middlewares.use("/data", (req, res, next) => {
        const filePath = path.join(dataDir, decodeURIComponent(req.url.split("?")[0]));
        if (!filePath.startsWith(dataDir)) return next();
        fs.readFile(filePath, (err, content) => {
          if (err) return next();
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(content);
        });
      });
    },
    // configureServer는 dev 서버 전용이라 프로덕션 빌드(vite build)에는 적용되지 않는다.
    // 빌드 결과물에도 같은 데이터를 정적 파일로 내보내기 위해 빌드 완료 시 dist/data/로 복사한다.
    closeBundle() {
      const outDir = path.resolve(__dirname, "dist", "data");
      fs.mkdirSync(outDir, { recursive: true });
      for (const file of fs.readdirSync(dataDir)) {
        if (file.endsWith(".json")) {
          fs.copyFileSync(path.join(dataDir, file), path.join(outDir, file));
        }
      }
    },
  };
}

export default defineConfig({
  envDir: "..",
  plugins: [react(), serveProjectData()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
