import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import methodologyContent from "../content/methodology.bg.md?raw";
import { text } from "../i18n/resources";
import { MetricIcon } from "../components/common/MetricIcon";
import { scoreLabels } from "../components/statements/ScorePanel";

const bibliographyHeading = "## Избрана библиография";
const [mainMethodologyContent, bibliographyContent] = methodologyContent.split(bibliographyHeading);

const criteria = [
  {
    label: scoreLabels.factual_accuracy,
    description: text.methodology.criteria.factualAccuracy
  },
  {
    label: scoreLabels.logical_consistency,
    description: text.methodology.criteria.logicalConsistency
  },
  {
    label: scoreLabels.communicational_integrity,
    description: text.methodology.criteria.communicationalIntegrity
  },
  {
    label: scoreLabels.principle_consistency,
    description: text.methodology.criteria.principleConsistency
  }
];

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ children, href }) => (
          <a href={href} rel="noreferrer" target={href?.startsWith("http") ? "_blank" : undefined}>
            {children}
          </a>
        )
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function MethodologyIntro() {
  return (
    <section className="methodology-intro-card">
      <p className="eyebrow">{text.methodology.introEyebrow}</p>
      <h2>{text.methodology.introTitle}</h2>
      <p>{text.methodology.introText}</p>
    </section>
  );
}

function MethodologyCriteriaCards() {
  return (
    <section className="methodology-criteria-grid" aria-label={text.methodology.criteriaAria}>
      {criteria.map((criterion) => (
        <article key={criterion.label}>
          <MetricIcon type="methodology" />
          <h2>{criterion.label}</h2>
          <p>{criterion.description}</p>
        </article>
      ))}
    </section>
  );
}

function MethodologyContent() {
  return (
    <>
      <div className="methodology-document">
        <MarkdownContent content={mainMethodologyContent.trim()} />
      </div>
      {bibliographyContent ? (
        <section className="methodology-bibliography">
          <details>
            <summary>{text.methodology.bibliographySummary}</summary>
            <div className="methodology-bibliography-content">
              <MarkdownContent content={`${bibliographyHeading}\n${bibliographyContent}`.trim()} />
            </div>
          </details>
        </section>
      ) : null}
    </>
  );
}

export function MethodologyPage() {
  return (
    <article className="methodology-page">
      <div className="detail-hero methodology-hero">
        <p className="eyebrow">{text.methodology.eyebrow}</p>
        <h1>{text.methodology.title}</h1>
        <Link className="button-secondary" to="/">
          {text.methodology.backToHome}
        </Link>
      </div>
      <MethodologyIntro />
      <MethodologyCriteriaCards />
      <MethodologyContent />
    </article>
  );
}
