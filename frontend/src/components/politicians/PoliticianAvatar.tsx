import type { Politician } from "../../types/politician";
import { formatResource, text } from "../../i18n/resources";

export function politicianInitials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

export function PoliticianAvatar({ politician, className = "" }: { politician: Politician; className?: string }) {
  const label = formatResource(text.politicians.noPicture, { name: politician.full_name });
  if (politician.image_url) {
    return <img className={`profile-photo ${className}`} src={politician.image_url} alt={politician.full_name} />;
  }
  return (
    <div className={`profile-photo placeholder ${className}`} aria-label={label}>
      {politicianInitials(politician.full_name) || "?"}
    </div>
  );
}
