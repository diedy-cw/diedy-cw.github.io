// 逐格輸出動畫：node render.mjs <輸出.mp4 或 --stills 目錄 秒數...> [--fps 30] [--audio 音軌.wav] [--no-subs]
// 需要 Playwright（Chromium）與 ffmpeg。動畫原始檔為 ../animation.html。
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const fps = +opt("--fps", 30);
const audio = opt("--audio", null);
const subs = !args.includes("--no-subs");

const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY, bypass: "localhost,127.0.0.1" } : undefined;
const browser = await chromium.launch({ proxy });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(pathToFileURL(path.join(root, "animation.html")).href + "?render", { waitUntil: "networkidle" });
await page.evaluate(async s => { await window.ready; window.setSubs(s); }, subs);
const grab = t => page.evaluate(t => { window.renderAt(t); return document.getElementById("c").toDataURL("image/jpeg", 0.94).split(",")[1]; }, t);

if (args[0] === "--stills") {
  const dir = args[1]; await mkdir(dir, { recursive: true });
  for (const t of args.slice(2).filter(a => !a.startsWith("--") && !isNaN(+a))) {
    await writeFile(path.join(dir, `t${(+t).toFixed(1).padStart(4, "0")}.jpg`), Buffer.from(await grab(+t), "base64"));
  }
} else {
  const out = args[0], total = Math.round(90 * fps);
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
    ...(audio ? ["-i", audio, "-c:a", "aac", "-b:a", "192k"] : []),
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", out], { stdio: ["pipe", "inherit", "inherit"] });
  for (let i = 0; i < total; i++) {
    const buf = Buffer.from(await grab(i / fps), "base64");
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on("close", r));
}
await browser.close();
