import type { PoliticalParty } from "../../types/politicalParty";
import { PartyCard } from "./PartyCard";

export function PartyList({ parties }: { parties: PoliticalParty[] }) {
  return (
    <div className="grid entity-list">
      {parties.map((party) => (
        <PartyCard key={party.id} party={party} />
      ))}
    </div>
  );
}
