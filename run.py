"""
zero_carbon_park_agent 一键运行脚本
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="zero_carbon_park_agent 零碳园区智慧能源与水务智能体系统")
    parser.add_argument("command", nargs="?", default="run",
                        choices=["init", "train", "run", "demo"],
                        help="命令: init(初始化), train(训练模型), run(启动服务), demo(演示工作流)")
    args = parser.parse_args()

    if args.command == "init":
        print("初始化系统...")
        from backend.init_db import main as init_main
        init_main()

    elif args.command == "train":
        print("训练模型...")
        from backend.train_model import main as train_main
        train_main()

    elif args.command == "run":
        print("启动服务...")
        import uvicorn
        from backend.config import API_HOST, API_PORT
        uvicorn.run(
            "backend.main:app",
            host=API_HOST,
            port=API_PORT,
            reload=True,
        )

    elif args.command == "demo":
        print("演示工作流...")
        from db.postgres_client import init_db
        from graph.graph_builder import init_knowledge_graph

        print("[1/3] 初始化数据库...")
        init_db()
        print("[2/3] 初始化知识图谱...")
        init_knowledge_graph()
        print("[3/3] 模拟数据已就绪（位于 backend/data/）")

        print("\n[4/4] 执行水质异常处置工作流...")
        from workflows.water_anomaly_workflow import run_water_anomaly_workflow
        result = run_water_anomaly_workflow({"device_id": "WQ-001"})

        print("\n" + "=" * 60)
        print("工作流执行结果:")
        print("=" * 60)
        print(f"工作流 ID: {result.get('workflow_id')}")
        print(f"异常类型: {result.get('anomaly_type')}")
        print(f"严重程度: {result.get('anomaly_severity')}")
        print(f"处置动作: {len(result.get('actions', []))} 项")
        print(f"工单 ID: {result.get('task_id')}")
        print(f"\n报告预览:\n{result.get('report_content', '无')[:500]}...")
        print("=" * 60)


if __name__ == "__main__":
    main()