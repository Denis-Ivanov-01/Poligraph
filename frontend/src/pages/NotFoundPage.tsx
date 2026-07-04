import { Link } from "react-router-dom";
import { text } from "../i18n/resources";

export function NotFoundPage() {
  return (
    <section className="section">
      <h1>{text.notFound.title}</h1>
      <p>{text.notFound.message}</p>
      <Link to="/">{text.notFound.back}</Link>
    </section>
  );
}
