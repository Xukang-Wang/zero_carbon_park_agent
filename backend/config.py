"""
zero_carbon_park_agent 全局配置管理
零碳园区智慧能源与水务智能体系统
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 加载 .env 文件
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # 尝试从当前目录加载

# ── 数据库配置（SQLite，轻量级无需额外安装）──────────────────────────────
DATABASE_URL = os.getenv("ZERO_CARBON_PARK_AGENT_DB_URL", f"sqlite:///{PROJECT_ROOT}/data/zero_carbon_park_agent.db")

# ── LLM 云端 API 配置（用户自行填入）─────────────────────────────────────
LLM_API_KEY = os.getenv("ZERO_CARBON_PARK_AGENT_LLM_API_KEY", "your-api-key-here")
LLM_BASE_URL = os.getenv("ZERO_CARBON_PARK_AGENT_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("ZERO_CARBON_PARK_AGENT_LLM_MODEL", "gpt-4o-mini")  # 推荐使用 gpt-4o-mini 或 deepseek-chat

# ── 知识图谱配置（基于 NetworkX 内存图 + JSON 持久化）────────────────────
GRAPH_DATA_PATH = PROJECT_ROOT / "data" / "energy_graph.json"

# ── 时序预测模型配置 ─────────────────────────────────────────────────────
MODEL_DIR = PROJECT_ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 预测模型参数
SEQ_LEN = 72          # 输入序列长度（过去 72h）
PRED_LEN = 24         # 预测长度（未来 24h）
FEATURE_DIM = 8       # 特征维度（COD,氨氮,硝氮,pH,温度,DO,进水流量,污泥浓度）
HIDDEN_DIM = 64       # LSTM 隐藏层维度
NUM_HEADS = 4         # Transformer 多头注意力头数
NUM_LAYERS = 2        # Transformer Encoder 层数
DROPOUT = 0.1

# ── 水质告警阈值 ─────────────────────────────────────────────────────────
WATER_THRESHOLDS = {
    "cod":            {"warning": 250.0, "critical": 300.0},
    "ammonia_nitrogen": {"warning": 25.0,  "critical": 35.0},
    "nitrate_nitrogen": {"warning": 3.0,   "critical": 5.0},
}

# ── 碳排放因子 ───────────────────────────────────────────────────────────
GRID_EMISSION_FACTOR = 0.581  # tCO₂/MWh（2023 年中国电网平均排放因子）

# ── 数据采集配置 ─────────────────────────────────────────────────────────
DATA_COLLECTION_INTERVAL_H = 1     # 数据采集间隔（小时）
DATA_COLLECTION_DEVICES = ["WQ-001", "WQ-002"]

# ── 服务配置 ─────────────────────────────────────────────────────────────
API_HOST = os.getenv("ZERO_CARBON_PARK_AGENT_HOST", "0.0.0.0")
API_PORT = int(os.getenv("ZERO_CARBON_PARK_AGENT_PORT", "8000"))

# ── 新能源发电配置 ─────────────────────────────────────────────────────────
# 光伏预测模型参数
PV_FORECAST_SEQ_LEN = 48       # 输入序列长度（过去48h气象数据）
PV_FORECAST_HORIZON = 24       # 预测时长（未来24h）
PV_CAPACITY_KW = 5000          # 园区光伏装机容量 (kW)
WIND_CAPACITY_KW = 3000        # 园区风电装机容量 (kW)

# ── 储能配置 ─────────────────────────────────────────────────────────────
STORAGE_CAPACITY_KWH = 5000    # 储能容量 (kWh)
STORAGE_RATED_POWER_KW = 2500  # 储能额定功率 (kW)
STORAGE_SOC_MIN = 20           # 最低SOC (%)
STORAGE_SOC_MAX = 90           # 最高SOC (%)
STORAGE_CHARGE_EFF = 0.95      # 充电效率
STORAGE_DISCHARGE_EFF = 0.95   # 放电效率
STORAGE_CYCLE_COST = 0.05      # 每kWh循环老化成本 (元)

# ── 共享储能商业模式配置 ──────────────────────────────────────────────────
SHARED_STORAGE_CAPACITY_LEASE_FEE = 250  # 容量租赁费 (元/kW·年)
PEAK_VALLEY_SPREAD = 0.6       # 峰谷价差 (元/kWh)
ANCILLARY_SERVICE_INCOME = 0.128  # 辅助服务补偿 (元/kWh)

# ── 虚拟电厂 (VPP) 配置 ──────────────────────────────────────────────────
VPP_AGGREGATED_CAPACITY_MW = 10  # VPP聚合容量 (MW)
VPP_RESPONSE_TIME_MS = 100       # VPP响应时间 (ms)
VPP_MIN_BID_PRICE = 0.3          # VPP最低报价 (元/kWh)
VPP_MAX_BID_PRICE = 1.5          # VPP最高报价 (元/kWh)

# ── 碳资产管理配置 ────────────────────────────────────────────────────────
CARBON_PRICE_FLOOR = 60          # 碳价下限 (元/吨)
CARBON_PRICE_CEILING = 100       # 碳价上限 (元/吨)
CCER_PRICE = 50                  # CCER价格 (元/吨)
GREEN_CERTIFICATE_PRICE = 25     # 绿证价格 (元/MWh)

# ── CCUS 配置 ─────────────────────────────────────────────────────────────
CCUS_CAPTURE_RATE = 0.90         # 碳捕集率
CCUS_CAPTURE_COST = 200          # 碳捕集成本 (元/吨CO₂)
CCUS_UTILIZATION_RATIO = 0.60    # 碳利用比例

# ── 零碳园区评价指标体系 ──────────────────────────────────────────────────
ZERO_CARBON_INDICATORS = {
    "carbon_intensity_decline": {"target": 20, "unit": "%", "category": "core"},
    "renewable_energy_ratio": {"target": 50, "unit": "%", "category": "guide"},
    "energy_intensity": {"target": "industry_advanced", "unit": "tce/万元", "category": "guide"},
    "green_building_ratio": {"target": 100, "unit": "%", "category": "guide"},
    "water_reuse_rate": {"target": 90, "unit": "%", "category": "guide"},
    "solid_waste_recycling_rate": {"target": 95, "unit": "%", "category": "guide"},
}

# ── 生物质能配置 ──────────────────────────────────────────────────────────
BIOMASS_CHP_CAPACITY_KW = 2000   # 生物质CHP装机容量 (kW)
BIOMASS_FEEDSTOCK_T_PER_DAY = 50  # 生物质原料日消耗 (吨/天)
BIOGAS_YIELD_M3_PER_T = 120      # 沼气产率 (m³/吨原料)
BIOGAS_METHANE_RATIO = 0.60      # 沼气甲烷含量

# ── 经济性分析配置 ────────────────────────────────────────────────────────
PV_INSTALL_COST_PER_W = 3.5      # 光伏安装成本 (元/W)
STORAGE_INSTALL_COST_PER_WH = 1.0  # 储能安装成本 (元/Wh)
DISCOUNT_RATE = 0.08             # 折现率
PROJECT_LIFETIME_YEARS = 20      # 项目寿命 (年)
ELECTRICITY_PRICE = 0.6          # 电价 (元/kWh)