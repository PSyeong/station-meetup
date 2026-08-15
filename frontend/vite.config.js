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
  };
}

export default defineConfig({
  plugins: [react(), serveProjectData()],
});
