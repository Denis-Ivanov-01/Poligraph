import type { Politician } from "../../types/politician";
import { PoliticianCard } from "./PoliticianCard";

export function PoliticianList({ politicians }: { politicians: Politician[] }) {
  return (
    <div className="grid">
      {politicians.map((politician) => (
        <PoliticianCard key={politician.id} politician={politician} />
      ))}
    </div>
  );
}
