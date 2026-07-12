import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  getProgram,
  getProgramSectionCommitments,
  getProgramSectionSubsections,
  searchProgramCommitments,
  type ProgramCommitmentQuery
} from "../api/programs";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { text } from "../i18n/resources";
import type { Commitment, ProgramCommitmentsPage, ProgramDetails, ProgramSection } from "../types/program";
import { useAsync } from "../utils/useAsync";

const STATUS_KEYS = [
  "fulfilled",
  "kept_to_date",
  "in_progress",
  "delayed",
  "partially_fulfilled",
  "violated",
  "not_started",
  "condition_not_met",
  "not_due",
  "not_applicable",
  "unclear",
  "abandoned",
  "not_analyzed"
];
const CONFIDENCE_KEYS = ["high", "medium", "low"];
const PAGE_SIZE = 25;

type CachedSubsections = {
  data: ProgramSection[] | null;
  loading: boolean;
  error: string | null;
};

type CachedCommitments = {
  items: Commitment[];
  total: number;
  nextOffset: number | null;
  hasMore: boolean;
  loading: boolean;
  error: string | null;
};

function useDebouncedValue(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);
  return debounced;
}

function nonZeroStatuses(counts: Record<string, number>) {
  return STATUS_KEYS.map((key) => [key, counts[key] ?? 0] as const).filter(([, value]) => value > 0);
}

function totalCommitments(counts: Record<string, number>) {
  return Object.values(counts).reduce((sum, value) => sum + value, 0);
}

function commitmentCountLabel(count: number) {
  return count === 1 ? text.programs.commitmentSingular : text.programs.totalCommitments;
}

function StatusDistributionBar({ counts, compact = false }: { counts: Record<string, number>; compact?: boolean }) {
  const entries = nonZeroStatuses(counts);
  const total = totalCommitments(counts);
  if (!total) return <span className="program-muted-note">{text.programs.noCommitmentsShort}</span>;
  return (
    <div className={compact ? "status-distribution compact" : "status-distribution"}>
      <div className="status-distribution-bar" aria-hidden="true">
        {entries.map(([key, value]) => (
          <span className={`status-segment status-segment-${key}`} style={{ width: `${(value / total) * 100}%` }} key={key} />
        ))}
      </div>
      <div className="status-distribution-legend">
        {entries.map(([key, value]) => (
          <span key={key}>
            <strong>{value}</strong> {text.programs.statuses[key as keyof typeof text.programs.statuses]}
          </span>
        ))}
      </div>
    </div>
  );
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return text.common.notAvailable;
  return `${Math.round(value * 100)}%`;
}

function formatScore(value?: number | null) {
  if (value === null || value === undefined) return text.common.notAvailable;
  return `${value}/100`;
}

function ProgramScoreSummary({ program }: { program: ProgramDetails }) {
  const score = program.score_summary;
  if (!score) return null;
  return (
    <section className="program-score-strip" aria-label={text.programs.scoreSummary}>
      <div>
        <span>{text.programs.fulfillmentScore}</span>
        <strong>{formatScore(score.fulfillment_score)}</strong>
      </div>
      <div>
        <span>{text.programs.overallContributionScore}</span>
        <strong>{formatScore(score.overall_score)}</strong>
      </div>
      <div>
        <span>{text.programs.weightedCoverage}</span>
        <strong>{formatPercent(score.coverage)}</strong>
      </div>
      <div>
        <span>{text.programs.dueCommitments}</span>
        <strong>{score.due_commitments}</strong>
      </div>
      <div>
        <span>{text.programs.indeterminateContribution}</span>
        <strong>{score.indeterminate_contribution_count}</strong>
      </div>
      <div>
        <span>{text.programs.violations}</span>
        <strong>{score.violated_count}</strong>
      </div>
    </section>
  );
}

function ProgramHeader({ program }: { program: ProgramDetails }) {
  return (
    <header className="program-browser-header">
      <nav className="program-breadcrumb" aria-label={text.programs.breadcrumbLabel}>
        <Link to="/programs">{text.programs.title}</Link>
        <span>{program.title}</span>
      </nav>
      <p className="eyebrow">{text.programs.programEyebrow}</p>
      <h1>{program.title}</h1>
      <p className="program-browser-subtitle">{program.period_text || program.short_description || program.description || program.political_subject_name}</p>
      <div className="program-browser-meta">
        <span>{program.total_commitments ?? 0} {commitmentCountLabel(program.total_commitments ?? 0)}</span>
        {program.last_commitment_update ? <span>{text.programs.lastUpdated}: {program.last_commitment_update}</span> : null}
        {program.source_url ? <a href={program.source_url} rel="noreferrer" target="_blank">{text.common.source}</a> : null}
      </div>
      <StatusDistributionBar counts={program.status_counts ?? {}} />
      <ProgramScoreSummary program={program} />
    </header>
  );
}

function ProgramToolbar({
  search,
  status,
  confidence,
  sort,
  hasFilters,
  onSearch,
  onStatus,
  onConfidence,
  onSort,
  onClear
}: {
  search: string;
  status: string;
  confidence: string;
  sort: string;
  hasFilters: boolean;
  onSearch: (value: string) => void;
  onStatus: (value: string) => void;
  onConfidence: (value: string) => void;
  onSort: (value: string) => void;
  onClear: () => void;
}) {
  return (
    <form className="program-toolbar" role="search" onSubmit={(event) => event.preventDefault()}>
      <label>
        <span>{text.programs.searchLabel}</span>
        <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder={text.programs.searchPlaceholder} />
      </label>
      <label>
        <span>{text.programs.filters.status}</span>
        <select value={status} onChange={(event) => onStatus(event.target.value)}>
          <option value="">{text.programs.filters.all}</option>
          {STATUS_KEYS.map((key) => (
            <option value={key} key={key}>{text.programs.statuses[key as keyof typeof text.programs.statuses]}</option>
          ))}
        </select>
      </label>
      <label>
        <span>{text.programs.confidenceFilter}</span>
        <select value={confidence} onChange={(event) => onConfidence(event.target.value)}>
          <option value="">{text.programs.filters.all}</option>
          {CONFIDENCE_KEYS.map((key) => (
            <option value={key} key={key}>{text.programs.confidence[key as keyof typeof text.programs.confidence]}</option>
          ))}
        </select>
      </label>
      <label>
        <span>{text.programs.sortLabel}</span>
        <select value={sort} onChange={(event) => onSort(event.target.value)}>
          <option value="order">{text.programs.sortOrder}</option>
          <option value="updated">{text.programs.sortUpdated}</option>
          <option value="title">{text.programs.sortTitle}</option>
          <option value="status">{text.programs.sortStatus}</option>
        </select>
      </label>
      {hasFilters ? <button type="button" className="button-secondary" onClick={onClear}>{text.programs.clearFilters}</button> : null}
    </form>
  );
}

function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="program-inline-skeleton" aria-live="polite" aria-label={text.common.loading}>
      {Array.from({ length: count }).map((_, index) => <span key={index} />)}
    </div>
  );
}

function InlineError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="program-inline-error">
      <span>{message}</span>
      <button type="button" onClick={onRetry}>{text.programs.retry}</button>
    </div>
  );
}

function CommitmentListRow({ commitment, returnSearch }: { commitment: Commitment; returnSearch: string }) {
  const description = commitment.normalized_description?.trim();
  const title = commitment.title.trim();
  const showDescription = description && description.toLocaleLowerCase() !== title.toLocaleLowerCase();
  const meta = [
    commitment.confidence_label,
    commitment.contribution_label ? `${text.programs.contribution}: ${commitment.contribution_label}` : null,
    commitment.importance_label ? `${text.programs.importance}: ${commitment.importance_label}` : null,
    commitment.evidence_count > 0 ? `${commitment.evidence_count} ${text.programs.evidenceShort}` : null,
    commitment.last_status_update ? `${text.programs.lastUpdated}: ${commitment.last_status_update}` : null
  ].filter(Boolean);
  return (
    <Link className={`commitment-row status-rail-${commitment.status}`} to={`/programs/${commitment.program.id}/commitments/${commitment.slug}${returnSearch}`}>
      <span className="commitment-row-rail" aria-hidden="true" />
      <span className={`status-badge status-${commitment.status}`}>{commitment.status_label}</span>
      <span className="commitment-row-main">
        <strong>{commitment.display_code ? `${commitment.display_code} ` : ""}{commitment.title}</strong>
        {showDescription ? <span className="commitment-row-description">{description}</span> : null}
        {meta.length ? <span className="commitment-row-meta">{meta.join(` ${text.common.separator} `)}</span> : null}
      </span>
      <span className="program-chevron" aria-hidden="true">›</span>
    </Link>
  );
}

function LoadMoreButton({ page, onLoadMore }: { page?: CachedCommitments; onLoadMore: () => void }) {
  if (!page?.items.length) return null;
  return (
    <div className="commitment-list-footer">
      <span>{text.programs.shown} {page.items.length} {text.programs.of} {page.total} {commitmentCountLabel(page.total)}</span>
      {page.hasMore ? (
        <button type="button" onClick={onLoadMore} disabled={page.loading}>
          {page.loading ? text.common.loading : text.programs.loadMore}
        </button>
      ) : null}
    </div>
  );
}

function CommitmentList({
  page,
  returnSearch,
  onLoadMore,
  onRetry
}: {
  page?: CachedCommitments;
  returnSearch: string;
  onLoadMore: () => void;
  onRetry: () => void;
}) {
  if (page?.loading && !page.items.length) return <SkeletonRows />;
  if (page?.error && !page.items.length) return <InlineError message={page.error} onRetry={onRetry} />;
  if (!page?.items.length) return <p className="program-muted-note">{text.programs.emptyCommitments}</p>;
  return (
    <div className="commitment-list">
      {page.items.map((commitment) => (
        <CommitmentListRow commitment={commitment} returnSearch={returnSearch} key={commitment.id} />
      ))}
      {page.error ? <InlineError message={page.error} onRetry={onRetry} /> : null}
      <LoadMoreButton page={page} onLoadMore={onLoadMore} />
    </div>
  );
}

function SubsectionAccordion({
  subsection,
  expanded,
  commitmentPage,
  returnSearch,
  onToggle,
  onLoadMore,
  onRetry
}: {
  subsection: ProgramSection;
  expanded: boolean;
  commitmentPage?: CachedCommitments;
  returnSearch: string;
  onToggle: () => void;
  onLoadMore: () => void;
  onRetry: () => void;
}) {
  const controlId = `subsection-${subsection.id}`;
  return (
    <article className="program-subsection-row">
      <button type="button" aria-expanded={expanded} aria-controls={controlId} onClick={onToggle}>
        <span className="program-node-number">{subsection.section_code || subsection.display_order}</span>
        <span className="program-node-main">
          <strong>{subsection.title}</strong>
          <span>{subsection.commitment_count} {commitmentCountLabel(subsection.commitment_count)}</span>
        </span>
        <StatusDistributionBar counts={subsection.status_counts} compact />
        <span className="program-chevron" aria-hidden="true">{expanded ? "⌃" : "⌄"}</span>
      </button>
      {expanded ? (
        <div className="program-subsection-content" id={controlId}>
          <CommitmentList page={commitmentPage} returnSearch={returnSearch} onLoadMore={onLoadMore} onRetry={onRetry} />
        </div>
      ) : null}
    </article>
  );
}

function SectionAccordion({
  section,
  expanded,
  cache,
  directCommitments,
  openSubsectionId,
  commitmentPages,
  returnSearch,
  onToggle,
  onRetrySection,
  onToggleSubsection,
  onLoadMore
}: {
  section: ProgramSection;
  expanded: boolean;
  cache?: CachedSubsections;
  directCommitments?: CachedCommitments;
  openSubsectionId: string | null;
  commitmentPages: Record<string, CachedCommitments>;
  returnSearch: string;
  onToggle: () => void;
  onRetrySection: () => void;
  onToggleSubsection: (subsectionId: string) => void;
  onLoadMore: (sectionId: string, reset?: boolean) => void;
}) {
  const controlId = `section-${section.id}`;
  return (
    <section className="program-section-card">
      <button type="button" className="program-section-control" aria-expanded={expanded} aria-controls={controlId} onClick={onToggle}>
        <span className="program-section-number">{section.section_code || String(section.display_order).padStart(2, "0")}</span>
        <span className="program-section-main">
          <strong>{section.title}</strong>
          {section.summary ? <span className="program-section-summary-text">{section.summary}</span> : null}
          <span>{section.commitment_count} {commitmentCountLabel(section.commitment_count)}</span>
        </span>
        <StatusDistributionBar counts={section.status_counts} compact />
        <span className="program-chevron" aria-hidden="true">{expanded ? "⌃" : "⌄"}</span>
      </button>
      {expanded ? (
        <div className="program-section-content" id={controlId}>
          {cache?.loading && !cache.data ? <SkeletonRows /> : null}
          {cache?.error ? <InlineError message={cache.error} onRetry={onRetrySection} /> : null}
          {section.direct_commitment_count > 0 ? (
            <div className="program-direct-commitments">
              <h3>{text.programs.directCommitments}</h3>
              <CommitmentList
                page={directCommitments}
                returnSearch={returnSearch}
                onLoadMore={() => onLoadMore(section.id)}
                onRetry={() => onLoadMore(section.id, true)}
              />
            </div>
          ) : null}
          {cache?.data?.length ? (
            <div className="program-subsection-list">
              {cache.data.map((subsection) => (
                <SubsectionAccordion
                  subsection={subsection}
                  expanded={openSubsectionId === subsection.id}
                  commitmentPage={commitmentPages[subsection.id]}
                  returnSearch={returnSearch}
                  onToggle={() => onToggleSubsection(subsection.id)}
                  onLoadMore={() => onLoadMore(subsection.id)}
                  onRetry={() => onLoadMore(subsection.id, true)}
                  key={subsection.id}
                />
              ))}
            </div>
          ) : null}
          {cache?.data && !cache.data.length && section.direct_commitment_count === 0 ? (
            <p className="program-muted-note">{text.programs.noCommitmentsShort}</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function SearchResults({
  page,
  loading,
  error,
  returnSearch,
  onLoadMore,
  onRetry,
  onBack
}: {
  page: CachedCommitments | null;
  loading: boolean;
  error: string | null;
  returnSearch: string;
  onLoadMore: () => void;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <section className="program-search-results">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.programs.searchResults}</p>
          <h2>{page?.total ?? 0} {text.programs.results}</h2>
        </div>
        <button type="button" className="button-secondary" onClick={onBack}>{text.programs.backToHierarchy}</button>
      </div>
      {loading && !page?.items.length ? <SkeletonRows count={5} /> : null}
      {error && !page?.items.length ? <InlineError message={error} onRetry={onRetry} /> : null}
      {page?.items.length ? (
        <CommitmentList page={page} returnSearch={returnSearch} onLoadMore={onLoadMore} onRetry={onRetry} />
      ) : !loading && !error ? (
        <EmptyState message={text.programs.emptyCommitments} />
      ) : null}
    </section>
  );
}

export function ProgramDetailsPage() {
  const { id = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data, loading, error } = useAsync(() => getProgram(id), [id]);
  const [sectionCache, setSectionCache] = useState<Record<string, CachedSubsections>>({});
  const [commitmentCache, setCommitmentCache] = useState<Record<string, CachedCommitments>>({});
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [confidence, setConfidence] = useState("");
  const [sort, setSort] = useState("order");
  const [searchPage, setSearchPage] = useState<CachedCommitments | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchRetry, setSearchRetry] = useState(0);
  const debouncedSearch = useDebouncedValue(search, 350);
  const openSectionId = searchParams.get("section");
  const openSubsectionId = searchParams.get("subsection");
  const hasFilters = Boolean(debouncedSearch.trim() || status || confidence || sort !== "order");
  const returnSearch = useMemo(() => {
    const params = new URLSearchParams();
    if (openSectionId) params.set("section", openSectionId);
    if (openSubsectionId) params.set("subsection", openSubsectionId);
    const value = params.toString();
    return value ? `?${value}` : "";
  }, [openSectionId, openSubsectionId]);

  const setHierarchy = (sectionId: string | null, subsectionId: string | null = null) => {
    const params = new URLSearchParams(searchParams);
    if (sectionId) params.set("section", sectionId);
    else params.delete("section");
    if (subsectionId) params.set("subsection", subsectionId);
    else params.delete("subsection");
    setSearchParams(params, { replace: false });
  };

  const loadSection = (sectionId: string, force = false) => {
    const cached = sectionCache[sectionId];
    if (!force && (cached?.data || cached?.loading)) return;
    setSectionCache((current) => ({ ...current, [sectionId]: { data: cached?.data ?? null, loading: true, error: null } }));
    getProgramSectionSubsections(id, sectionId)
      .then((response) => {
        setSectionCache((current) => ({ ...current, [sectionId]: { data: response.items, loading: false, error: null } }));
      })
      .catch((requestError: unknown) => {
        setSectionCache((current) => ({
          ...current,
          [sectionId]: {
            data: current[sectionId]?.data ?? null,
            loading: false,
            error: requestError instanceof Error ? requestError.message : "Unknown error"
          }
        }));
      });
  };

  const loadCommitments = (sectionId: string, reset = false) => {
    const cached = commitmentCache[sectionId];
    if (!reset && cached?.loading) return;
    const offset = reset ? 0 : cached?.nextOffset ?? 0;
    if (!reset && cached && cached.items.length > 0 && cached.nextOffset === null) return;
    setCommitmentCache((current) => ({
      ...current,
      [sectionId]: {
        items: reset ? [] : current[sectionId]?.items ?? [],
        total: reset ? 0 : current[sectionId]?.total ?? 0,
        nextOffset: reset ? 0 : current[sectionId]?.nextOffset ?? 0,
        hasMore: reset ? true : current[sectionId]?.hasMore ?? true,
        loading: true,
        error: null
      }
    }));
    getProgramSectionCommitments(id, sectionId, { limit: PAGE_SIZE, offset })
      .then((page) => {
        setCommitmentCache((current) => ({
          ...current,
          [sectionId]: {
            items: reset ? page.items : [...(current[sectionId]?.items ?? []), ...page.items],
            total: page.total_count,
            nextOffset: page.next_offset ?? null,
            hasMore: page.has_more,
            loading: false,
            error: null
          }
        }));
      })
      .catch((requestError: unknown) => {
        setCommitmentCache((current) => ({
          ...current,
          [sectionId]: {
            items: current[sectionId]?.items ?? [],
            total: current[sectionId]?.total ?? 0,
            nextOffset: current[sectionId]?.nextOffset ?? 0,
            hasMore: current[sectionId]?.hasMore ?? true,
            loading: false,
            error: requestError instanceof Error ? requestError.message : "Unknown error"
          }
        }));
      });
  };

  useEffect(() => {
    if (!openSectionId) return;
    loadSection(openSectionId);
    const section = data?.sections.find((item) => item.id === openSectionId);
    if (section?.direct_commitment_count) loadCommitments(openSectionId);
  }, [openSectionId, data]);

  useEffect(() => {
    if (!openSectionId || !openSubsectionId) return;
    const subsections = sectionCache[openSectionId]?.data;
    if (subsections?.some((item) => item.id === openSubsectionId)) {
      loadCommitments(openSubsectionId);
    }
  }, [openSectionId, openSubsectionId, sectionCache]);

  useEffect(() => {
    if (!hasFilters) {
      setSearchPage(null);
      setSearchError(null);
      setSearchLoading(false);
      return;
    }
    const controller = new AbortController();
    setSearchLoading(true);
    setSearchError(null);
    const query: ProgramCommitmentQuery = {
      q: debouncedSearch.trim(),
      status,
      confidence,
      sort,
      limit: PAGE_SIZE,
      offset: 0
    };
    searchProgramCommitments(id, query, controller.signal)
      .then((page) => {
        setSearchPage({
          items: page.items,
          total: page.total_count,
          nextOffset: page.next_offset ?? null,
          hasMore: page.has_more,
          loading: false,
          error: null
        });
        setSearchLoading(false);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setSearchPage(null);
        setSearchError(requestError instanceof Error ? requestError.message : "Unknown error");
        setSearchLoading(false);
      });
    return () => controller.abort();
  }, [id, debouncedSearch, status, confidence, sort, hasFilters, searchRetry]);

  const loadMoreSearch = () => {
    if (!searchPage?.hasMore || searchPage.loading) return;
    const offset = searchPage.nextOffset ?? searchPage.items.length;
    setSearchPage({ ...searchPage, loading: true, error: null });
    searchProgramCommitments(id, { q: debouncedSearch.trim(), status, confidence, sort, limit: PAGE_SIZE, offset })
      .then((page) => {
        setSearchPage((current) => ({
          items: [...(current?.items ?? []), ...page.items],
          total: page.total_count,
          nextOffset: page.next_offset ?? null,
          hasMore: page.has_more,
          loading: false,
          error: null
        }));
      })
      .catch((requestError: unknown) => {
        setSearchPage((current) => ({
          items: current?.items ?? [],
          total: current?.total ?? 0,
          nextOffset: current?.nextOffset ?? 0,
          hasMore: current?.hasMore ?? true,
          loading: false,
          error: requestError instanceof Error ? requestError.message : "Unknown error"
        }));
      });
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.programs.programNotFound} />;

  return (
    <article className="section program-browser">
      <ProgramHeader program={data} />
      {data.source_coverage_status === "partial" ? <p className="analysis-disclaimer">{text.programs.partialSourceWarning}</p> : null}
      {data.source_acquisition_method === "source_not_found" ? <p className="analysis-disclaimer">{text.programs.sourceNotFoundWarning}</p> : null}
      {data.source_acquisition_note ? <p className="muted">{data.source_acquisition_note}</p> : null}
      <ProgramToolbar
        search={search}
        status={status}
        confidence={confidence}
        sort={sort}
        hasFilters={hasFilters}
        onSearch={setSearch}
        onStatus={setStatus}
        onConfidence={setConfidence}
        onSort={setSort}
        onClear={() => {
          setSearch("");
          setStatus("");
          setConfidence("");
          setSort("order");
        }}
      />
      {hasFilters ? (
        <SearchResults
          page={searchPage}
          loading={searchLoading}
          error={searchError}
          returnSearch={returnSearch}
          onLoadMore={loadMoreSearch}
          onRetry={() => setSearchRetry((value) => value + 1)}
          onBack={() => {
            setSearch("");
            setStatus("");
            setConfidence("");
            setSort("order");
          }}
        />
      ) : data.sections.length ? (
        <div className="program-section-stack">
          {data.sections.map((section) => (
            <SectionAccordion
              section={section}
              expanded={openSectionId === section.id}
              cache={sectionCache[section.id]}
              directCommitments={commitmentCache[section.id]}
              openSubsectionId={openSubsectionId}
              commitmentPages={commitmentCache}
              returnSearch={returnSearch}
              onToggle={() => setHierarchy(openSectionId === section.id ? null : section.id)}
              onRetrySection={() => loadSection(section.id, true)}
              onToggleSubsection={(subsectionId) => {
                if (openSubsectionId === subsectionId) setHierarchy(section.id);
                else {
                  setHierarchy(section.id, subsectionId);
                  loadCommitments(subsectionId);
                }
              }}
              onLoadMore={loadCommitments}
              key={section.id}
            />
          ))}
        </div>
      ) : (
        <EmptyState message={text.programs.emptyCommitments} />
      )}
      <p className="analysis-disclaimer">{data.disclaimer || text.programs.structuralDisclaimer}</p>
    </article>
  );
}
