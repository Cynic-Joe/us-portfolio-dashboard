# US Portfolio Dashboard

Jake 的小额美股组合 dashboard。

## 功能

- 维护持仓、成本、现价、目标仓位
- 自动计算总资产、仓位占比、目标缺口、建议补仓股数
- 内置每笔约 1 USD 平台费的分批补仓阈值
- GitHub Pages 云端查看
- GitHub Actions 用 Finnhub secret 定时生成 `quotes/latest.json`

## 云端报价

仓库需要设置 Actions secret：

- `FINNHUB_API_KEY`

然后运行 workflow：`Update Finnhub Quotes`。

## 本地运行

```bash
python server.py
# open http://127.0.0.1:8766/
```
