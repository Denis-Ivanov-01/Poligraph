import { Link } from "react-router-dom";

import { getMethodology } from "../api/resources";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { text } from "../i18n/resources";
import { useAsync } from "../utils/useAsync";
import { MethodologyContent } from "./StatementsMethodologyPage";

export function ControversialTopicsMethodologyPage() {
  const { data: methodologyContent, loading, error } = useAsync(
    () => getMethodology("controversial-topics"),
    []
  );

  return (
    <article className="methodology-page">
      <div className="detail-hero methodology-hero">
        <p className="eyebrow">{text.methodology.eyebrow}</p>
        <h1>{text.methodology.controversialTopicsTitle}</h1>
        <Link className="button-secondary" to="/">
          {text.methodology.backToHome}
        </Link>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {methodologyContent ? <MethodologyContent content={methodologyContent} /> : null}
    </article>
  );
}
