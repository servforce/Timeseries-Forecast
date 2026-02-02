# Frontend（按 `server/CDD.md` 第六章实现）

## 目标
- 仅上传 Markdown（`.md`），Markdown 内包含 ```json 代码块
- 支持两种模式：
  - Zero-shot：调用后端 `POST /zeroshot/`
  - Finetune：调用后端 `POST /finetune/`
- 结果展示：多 `item_id` 切换、折线图（P50/mean）+ 区间带（P10-P90 优先）、表格与下载

## 运行（本机 Node 环境）
1) 进入目录：`cd frontend`
2) 配置后端地址：复制 `.env.example` 为 `.env` 并修改 `VITE_API_BASE_URL`
3) 安装依赖：`npm install`
4) 启动开发：`npm run dev`

默认前端端口：`http://localhost:5173`

## 常见问题：点击预测显示 “Network Error”
通常是以下两种原因之一：
1) **后端没启动 / 端口不通**：先在浏览器打开 `http://localhost:5001/health` 验证后端可访问。
2) **你用 Network 地址访问了前端**（例如 `http://10.0.1.224:5173`）：
   - 此时前端默认调用的 `http://localhost:5001` 会变成“访问你当前设备的 localhost”，会直接连不上。
   - 解决：把 `.env` 里的 `VITE_API_BASE_URL` 改成 `http://10.0.1.224:5001`，然后**重启** `npm run dev`。

## 分位数说明
- Quantiles 支持 `0.05 ~ 0.95`（步长 `0.05`），共 19 个可选项
- 可视化默认展示：
  - 主线：P50（优先使用 `0.5` 列；若没有则回退 `mean`）
  - 阴影区间：P10-P90（优先使用 `0.1` 与 `0.9`；若没有则回退到最小/最大可用分位数列）

## 指标与提示
- 可选指标：WQL / WAPE / IC / IR
- 若 IC/IR 不能计算，会展示 warning（原因如历史长度不足、合并失败等）
- IC/IR 需要至少 `2 * prediction_length` 的历史长度

## 协变量开关（With Covariates）
- 关闭时：即使输入有协变量字段，也会被忽略
- 开启时：必须提供 `covariates`，且长度 = `prediction_length`

## 一键启动（推荐两种方式）
### 方式 A：脚本（本机安装了 Node + Python）
- 在仓库根目录执行：`bash scripts/dev.sh`

### 方式 B：Docker Compose（需要 docker 可联网构建前端）
- 在仓库根目录执行：`docker compose up --build`
- 前端：`http://localhost:5173`
- 后端：`http://localhost:5001/docs`

## 后端要求
- 后端已启动并可访问：
  - `http://localhost:5001/zeroshot/`
  - `http://localhost:5001/finetune/`
  - `http://localhost:5001/docs`

## 示例输入
- `frontend/public/sample_input.md` 可直接上传测试
