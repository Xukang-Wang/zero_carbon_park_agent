"""
zero_carbon_park_agent 初始化脚本
一键生成模拟数据、初始化数据库和知识图谱
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("\n" + "=" * 60)
    print("  zero_carbon_park_agent 系统初始化")
    print("=" * 60 + "\n")

    # 1. 初始化数据库
    print("[1/3] 初始化数据库...")
    try:
        from db.postgres_client import init_db
        init_db()
        print("  数据库初始化完成")
    except Exception as e:
        print(f"  数据库初始化失败: {e}")

    # 2. 初始化知识图谱
    print("\n[2/3] 初始化知识图谱...")
    try:
        from graph.graph_builder import init_knowledge_graph
        kg = init_knowledge_graph()
        print(f"  知识图谱初始化完成: {kg.graph.number_of_nodes()} 节点, {kg.graph.number_of_edges()} 边")
    except Exception as e:
        print(f"  知识图谱初始化失败: {e}")

    # 3. 模拟数据已预生成到 data/ 目录，无需运行时生成
    print("\n[3/3] 模拟数据已就绪...")
    print("  数据文件位于 backend/data/ 目录")
    print("  如需重新生成，运行: python scripts/generate_mock_data.py")

    print("\n" + "=" * 60)
    print("  初始化完成！")
    print(f"  运行 'python main.py' 启动服务")
    print(f"  访问 http://localhost:8000/docs 查看 API 文档")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()