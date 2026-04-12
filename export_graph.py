import json
from pathlib import Path

from realneighborhood import build_real_neighborhood_graph


def main():
    graph, _, _ = build_real_neighborhood_graph()
    output_path = Path("web") / "data" / "neighborhood_graph.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(graph.to_dict(), output_file, indent=2)

    print(f"Exported graph to {output_path}")


if __name__ == "__main__":
    main()
