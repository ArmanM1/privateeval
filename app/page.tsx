"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

type View = "overview" | "compare" | "robustness" | "privacy" | "review" | "method";
type Choice = "A" | "B" | "Tie";
type ResultBundle = Record<string, any>;

const MODEL_COLORS = ["#f36f4a", "#5f6de3", "#25a987", "#e5a93d"];

function formatNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatLatency(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`;
}

function cx(...items: Array<string | false | null | undefined>) {
  return items.filter(Boolean).join(" ");
}

function MetricCard({ eyebrow, value, detail, tone = "ink" }: { eyebrow: string; value: string; detail: string; tone?: string }) {
  return (
    <article className={cx("metric-card", `tone-${tone}`)}>
      <span className="eyebrow">{eyebrow}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <span className="pulse-dot" />
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}

export default function Home() {
  const [bundle, setBundle] = useState<ResultBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("overview");
  const [exampleId, setExampleId] = useState("");
  const [leftModel, setLeftModel] = useState("");
  const [rightModel, setRightModel] = useState("");
  const [reviewIndex, setReviewIndex] = useState(0);
  const [reviewChoices, setReviewChoices] = useState<Record<string, Choice>>({});
  const [reviewReasons, setReviewReasons] = useState<Record<string, string>>({});
  const [reviewerId, setReviewerId] = useState("reviewer-01");

  useEffect(() => {
    fetch("/results/result_bundle.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("The result bundle could not be loaded.");
        return response.json();
      })
      .then((data) => {
        setBundle(data);
        const modelIds = data.models.map((model: any) => model.id);
        const clean = data.records.filter((record: any) => record.slice === "clean");
        setExampleId(clean[0]?.example_id ?? "");
        setLeftModel(modelIds[1] ?? modelIds[0] ?? "");
        setRightModel(modelIds[2] ?? modelIds[0] ?? "");
      })
      .catch((reason) => setError(reason.message));
  }, []);

  const cleanRecords = useMemo(
    () => bundle?.records.filter((record: any) => record.slice === "clean") ?? [],
    [bundle],
  );
  const cleanExamples = useMemo(() => {
    const seen = new Map<string, any>();
    for (const record of cleanRecords) if (!seen.has(record.example_id)) seen.set(record.example_id, record);
    return Array.from(seen.values());
  }, [cleanRecords]);

  if (error) return <main className="load-screen"><EmptyState title="Bundle unavailable" detail={error} /></main>;
  if (!bundle) return <main className="load-screen"><EmptyState title="Opening the lab" detail="Loading the versioned result bundle…" /></main>;

  const aggregates = bundle.aggregates.models;
  const modelIndex = new Map(aggregates.map((model: any, index: number) => [model.model_id, { ...model, color: MODEL_COLORS[index % MODEL_COLORS.length] }]));
  const modelFor = (modelId: string) => modelIndex.get(modelId) as any;
  const recordFor = (modelId: string, id = exampleId) => cleanRecords.find((record: any) => record.model_id === modelId && record.example_id === id);
  const measured = bundle.run.claim_status === "provisional_measured_unverified";
  const fastest = [...aggregates].sort((a: any, b: any) => a.efficiency.median_latency_ms - b.efficiency.median_latency_ms)[0];
  const bestQuality = [...aggregates].sort((a: any, b: any) => b.quality.semantic_similarity.mean - a.quality.semantic_similarity.mean)[0];
  const neuralIds = new Set(bundle.models.filter((model: any) => model.kind === "transformers").map((model: any) => model.id));
  const neuralAggregates = aggregates.filter((model: any) => neuralIds.has(model.model_id));
  const lowestMemory = [...(neuralAggregates.length ? neuralAggregates : aggregates)].sort((a: any, b: any) => (a.efficiency.model_size_mb ?? Infinity) - (b.efficiency.model_size_mb ?? Infinity))[0];
  const privacyBest = [...bundle.analysis.privacy].sort((a: any, b: any) => a.normalized_copy_rate - b.normalized_copy_rate)[0];

  const nav: Array<{ id: View; label: string; mark: string }> = [
    { id: "overview", label: "Decision view", mark: "01" },
    { id: "compare", label: "Example lab", mark: "02" },
    { id: "robustness", label: "Stress tests", mark: "03" },
    { id: "privacy", label: "PII canaries", mark: "04" },
    { id: "review", label: "Blind review", mark: "05" },
    { id: "method", label: "Method & limits", mark: "06" },
  ];

  const chooseView = (next: View) => {
    setView(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand-lockup">
          <span className="brand-mark"><i /><i /><i /></span>
          <div><strong>PrivateEval</strong><small>local model laboratory</small></div>
        </div>
        <nav aria-label="Lab views">
          {nav.map((item) => (
            <button key={item.id} className={cx("nav-item", view === item.id && "active")} onClick={() => chooseView(item.id)} aria-current={view === item.id ? "page" : undefined}>
              <span>{item.mark}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="run-capsule">
          <div className="capsule-top"><span className={cx("status-light", measured ? "measured" : "simulated")} />{measured ? "Measured run" : "Smoke bundle"}</div>
          <strong>{bundle.run.id}</strong>
          <p>{bundle.environment.hardware_label}</p>
          <dl>
            <div><dt>examples</dt><dd>{bundle.aggregates.clean_examples}</dd></div>
            <div><dt>seed</dt><dd>{bundle.run.seed}</dd></div>
          </dl>
        </div>
        <p className="rail-note">No private documents.<br />No API judge.<br />No security guarantee.</p>
      </aside>

      <main className="main-canvas">
        <header className="top-bar">
          <div className="mobile-brand">PrivateEval</div>
          <div className="breadcrumb"><span>Evaluation lab</span><b>/</b>{nav.find((item) => item.id === view)?.label}</div>
          <div className="top-actions">
            <span className="artifact-chip">{bundle.run.claim_status.replaceAll("_", " ")}</span>
            <button className="ghost-button" onClick={() => chooseView("method")}>View protocol <span>↗</span></button>
          </div>
        </header>

        {view === "overview" && (
          <section className="view-wrap overview-view">
            <div className="hero-grid">
              <div className="hero-copy">
                <span className="kicker">CPU-FIRST / PAIRED / REPRODUCIBLE</span>
                <h1>Choose the tradeoff.<br /><em>See the evidence.</em></h1>
                <p>PrivateEval turns small-model summarization into an inspectable engineering decision across quality, speed, memory, robustness, and synthetic privacy behavior.</p>
                <div className="hero-actions">
                  <button className="primary-button" onClick={() => chooseView("compare")}>Inspect paired outputs <span>→</span></button>
                  <button className="text-button" onClick={() => chooseView("robustness")}>Open stress tests</button>
                </div>
              </div>
              <div className="hypothesis-card">
                <span className="eyebrow">REGISTERED QUESTION</span>
                <blockquote>Can INT8 cut interactive cost while keeping semantic quality within <b>0.05</b> of FP32?</blockquote>
                <div className="hypothesis-foot">
                  <span>Primary metric</span>
                  <strong>{bundle.protocol.semantic_metric}</strong>
                </div>
              </div>
            </div>

            {!measured && (
              <div className="truth-banner"><strong>Instrumentation preview</strong><span>This bundle contains simulated adapter configurations. It proves the pipeline and UI contract—not model performance.</span></div>
            )}

            <div className="metric-strip">
              <MetricCard eyebrow="BEST SEMANTIC SCORE" value={formatNumber(bestQuality.quality.semantic_similarity.mean, 3)} detail={bestQuality.label} tone="violet" />
              <MetricCard eyebrow="FASTEST WARM RESPONSE" value={formatLatency(fastest.efficiency.median_latency_ms)} detail={fastest.label} tone="coral" />
              <MetricCard eyebrow="SMALLEST NEURAL WEIGHTS" value={`${formatNumber(lowestMemory.efficiency.model_size_mb, 1)} MB`} detail={lowestMemory.label} tone="mint" />
              <MetricCard eyebrow="LOWEST CANARY COPY" value={`${formatNumber(privacyBest.normalized_copy_rate * 100, 0)}%`} detail={`${privacyBest.model_label} · synthetic, not a guarantee`} tone="sand" />
            </div>

            <div className="overview-panels">
              <TradeoffPlot models={aggregates} />
              <div className="rank-panel panel">
                <div className="panel-heading"><div><span className="eyebrow">PAIRED RESULTS</span><h2>Configuration ledger</h2></div><span className="panel-meta">95% bootstrap CI</span></div>
                <div className="rank-list">
                  {aggregates.map((model: any, index: number) => (
                    <button key={model.model_id} onClick={() => { setLeftModel(model.model_id); chooseView("compare"); }}>
                      <span className="rank-number">{String(index + 1).padStart(2, "0")}</span>
                      <span className="rank-name"><i style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }} />{model.label}<small>{model.provenance.replaceAll("_", " ")}</small></span>
                      <span className="rank-score">{formatNumber(model.quality.semantic_similarity.mean, 3)}<small>{formatLatency(model.efficiency.median_latency_ms)}</small></span>
                      <span className="rank-arrow">↗</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="evidence-row">
              <article><span>01</span><div><strong>Same inputs</strong><p>Every configuration receives the same bounded source, perturbation, and synthetic canary.</p></div></article>
              <article><span>02</span><div><strong>Uncertainty included</strong><p>Paired bootstrap intervals and effect sizes keep small differences in perspective.</p></div></article>
              <article><span>03</span><div><strong>Failures stay visible</strong><p>Every aggregate drills down to source, output, telemetry, and explicit provenance.</p></div></article>
            </div>
          </section>
        )}

        {view === "compare" && (
          <CompareView bundle={bundle} examples={cleanExamples} exampleId={exampleId} setExampleId={setExampleId} leftModel={leftModel} setLeftModel={setLeftModel} rightModel={rightModel} setRightModel={setRightModel} recordFor={recordFor} modelFor={modelFor} />
        )}

        {view === "robustness" && <RobustnessView bundle={bundle} modelIndex={modelIndex} />}
        {view === "privacy" && <PrivacyView bundle={bundle} />}
        {view === "review" && (
          <ReviewView bundle={bundle} reviewIndex={reviewIndex} setReviewIndex={setReviewIndex} choices={reviewChoices} setChoices={setReviewChoices} reasons={reviewReasons} setReasons={setReviewReasons} reviewerId={reviewerId} setReviewerId={setReviewerId} />
        )}
        {view === "method" && <MethodView bundle={bundle} />}
      </main>
    </div>
  );
}

function TradeoffPlot({ models }: { models: any[] }) {
  const latencies = models.map((model) => Math.max(0.1, model.efficiency.median_latency_ms));
  const qualities = models.map((model) => model.quality.semantic_similarity.mean);
  const logValues = latencies.map(Math.log10);
  const minX = Math.min(...logValues);
  const maxX = Math.max(...logValues);
  const minY = Math.min(...qualities) - 0.04;
  const maxY = Math.max(...qualities) + 0.04;
  return (
    <div className="tradeoff-panel panel">
      <div className="panel-heading"><div><span className="eyebrow">QUALITY × LATENCY</span><h2>Interactive frontier</h2></div><span className="panel-meta">upper-left wins</span></div>
      <div className="plot-wrap">
        <span className="axis-y">semantic similarity</span><span className="axis-x">warm latency →</span>
        <div className="plot-grid">
          {models.map((model, index) => {
            const left = 8 + ((Math.log10(Math.max(0.1, model.efficiency.median_latency_ms)) - minX) / (maxX - minX || 1)) * 82;
            const top = 85 - ((model.quality.semantic_similarity.mean - minY) / (maxY - minY || 1)) * 74;
            return <button key={model.model_id} className="plot-point" title={`${model.label}: ${formatNumber(model.quality.semantic_similarity.mean, 3)}, ${formatLatency(model.efficiency.median_latency_ms)}`} style={{ "--x": `${left}%`, "--y": `${top}%`, "--point": MODEL_COLORS[index % MODEL_COLORS.length] } as CSSProperties}><i /><span>{index + 1}</span></button>;
          })}
        </div>
        <div className="plot-legend">{models.map((model, index) => <span key={model.model_id}><i style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }} />{index + 1}. {model.label}</span>)}</div>
      </div>
    </div>
  );
}

function CompareView({ bundle, examples, exampleId, setExampleId, leftModel, setLeftModel, rightModel, setRightModel, recordFor, modelFor }: any) {
  const source = examples.find((item: any) => item.example_id === exampleId) ?? examples[0];
  const left = recordFor(leftModel);
  const right = recordFor(rightModel);
  return (
    <section className="view-wrap compare-view">
      <div className="section-intro"><div><span className="kicker">TRACEABLE OUTPUTS</span><h1>One source. Two configurations.</h1><p>Compare the words, then audit the evidence behind them.</p></div><div className="example-pager"><span>{String(examples.findIndex((item: any) => item.example_id === exampleId) + 1).padStart(2, "0")}</span><b>/</b>{String(examples.length).padStart(2, "0")}</div></div>
      <div className="control-bar">
        <label><span>Source example</span><select aria-label="Source example" value={exampleId} onChange={(event) => setExampleId(event.target.value)}>{examples.map((item: any) => <option key={item.example_id} value={item.example_id}>{item.title}</option>)}</select></label>
        <span className="control-separator" />
        <label><span>Left configuration</span><select aria-label="Left configuration" value={leftModel} onChange={(event) => setLeftModel(event.target.value)}>{bundle.models.map((model: any) => <option key={model.id} value={model.id}>{model.label}</option>)}</select></label>
        <span className="versus">VS</span>
        <label><span>Right configuration</span><select aria-label="Right configuration" value={rightModel} onChange={(event) => setRightModel(event.target.value)}>{bundle.models.map((model: any) => <option key={model.id} value={model.id}>{model.label}</option>)}</select></label>
      </div>
      {source && <article className="source-card"><div className="source-head"><div><span className="eyebrow">PUBLIC SOURCE · {source.topic.replaceAll("_", " ")}</span><h2>{source.title}</h2></div><span>{source.source.split(" ").length} words · bounded input</span></div><p>{source.source}</p></article>}
      <div className="output-grid">
        <OutputCard side="A" record={left} aggregate={modelFor(leftModel)} />
        <OutputCard side="B" record={right} aggregate={modelFor(rightModel)} />
      </div>
      {source && <article className="reference-strip"><span className="eyebrow">REFERENCE SUMMARY</span><p>{source.reference}</p><small>Public-domain fixture · not shown to adapters</small></article>}
    </section>
  );
}

function OutputCard({ side, record, aggregate }: any) {
  if (!record || !aggregate) return <div className="output-card"><p>No paired record available.</p></div>;
  const metrics = [
    ["Semantic", record.metrics.semantic_similarity],
    ["ROUGE-L", record.metrics.rouge_l],
    ["Support", record.metrics.source_support],
  ];
  return (
    <article className="output-card">
      <div className="output-head"><div><span className="side-badge">{side}</span><div><strong>{record.model_label}</strong><small>{record.provenance.replaceAll("_", " ")}</small></div></div><span className="latency-badge">{formatLatency(record.telemetry.latency_ms)}</span></div>
      <p className="output-text">{record.output || <em>Empty output</em>}</p>
      <div className="metric-bars">
        {metrics.map(([label, value]) => <div key={label as string}><span><b>{label}</b><strong>{formatNumber(value as number, 3)}</strong></span><i><u style={{ width: `${Math.max(0, Math.min(100, (value as number) * 100))}%` }} /></i></div>)}
      </div>
      <dl className="output-telemetry"><div><dt>Peak RSS</dt><dd>{formatNumber(record.telemetry.peak_rss_mb, 1)} MB</dd></div><div><dt>Model bytes</dt><dd>{formatNumber(aggregate.efficiency.model_size_mb, 1)} MB</dd></div><div><dt>Uncertainty proxy</dt><dd>{record.confidence === null ? "not available" : formatNumber(record.confidence, 3)}</dd></div><div><dt>Throughput</dt><dd>{formatNumber(record.telemetry.output_tokens_per_second, 1)} tok/s</dd></div></dl>
      <details><summary>Open raw trace <span>＋</span></summary><pre>{JSON.stringify({ record_id: record.record_id, model_id: record.model_id, generation: record.generation_metadata, repetitions_ms: record.telemetry.latency_repetitions_ms }, null, 2)}</pre></details>
    </article>
  );
}

function RobustnessView({ bundle, modelIndex }: any) {
  const rows = bundle.analysis.robustness;
  const perturbations = Array.from(new Set(rows.map((row: any) => row.perturbation))) as string[];
  return (
    <section className="view-wrap robustness-view">
      <div className="section-intro"><div><span className="kicker">CONTROLLED PERTURBATIONS</span><h1>Pressure-test the ranking.</h1><p>Quality deltas are paired against each model’s clean output for the same source.</p></div><div className="protocol-stamp"><strong>{rows[0]?.n ?? 0}</strong><span>paired sources<br />per perturbation</span></div></div>
      <div className="stress-grid">
        {perturbations.map((perturbation, index) => {
          const current = rows.filter((row: any) => row.perturbation === perturbation);
          const descriptions: Record<string, string> = { typos: "Adjacent characters swapped in 3% of longer words.", formatting: "Headings, bullets, tabs, and line breaks injected.", length_shift: "Benign routing text pushes the registered input boundary." };
          return <article className="stress-card" key={perturbation}><div className="stress-number">0{index + 1}</div><span className="eyebrow">{perturbation.replaceAll("_", " ")}</span><h2>{descriptions[perturbation]}</h2><div className="delta-bars">{current.map((row: any) => { const model = modelIndex.get(row.model_id); const width = Math.min(100, Math.abs(row.delta) * 500); return <div key={row.model_id}><span><b>{row.model_label}</b><strong className={row.delta < 0 ? "negative" : "positive"}>{row.delta > 0 ? "+" : ""}{formatNumber(row.delta, 3)}</strong></span><i><u style={{ width: `${Math.max(2, width)}%`, background: model?.color }} /></i></div>; })}</div><small>Δ registered semantic metric · n={current[0]?.n ?? 0}</small></article>;
        })}
      </div>
      <div className="failure-panel panel">
        <div className="panel-heading"><div><span className="eyebrow">LOWEST SUPPORT RECORDS</span><h2>Failure ledger</h2></div><span className="panel-meta">root-cause prompts, not excuses</span></div>
        <div className="failure-table"><div className="failure-row head"><span>Source</span><span>Configuration</span><span>Support</span><span>Root-cause hypothesis</span></div>{bundle.failures.slice(0, 4).map((record: any) => <div className="failure-row" key={`${record.record_id}-${record.model_id}`}><span>{record.title}<small>{record.example_id}</small></span><span>{record.model_label}</span><span>{formatNumber(record.metrics.source_support, 3)}</span><span>{record.metrics.source_support < 0.4 ? "Paraphrase/entity mismatch; inspect unsupported claims." : "Coverage compression or proxy disagreement."}</span></div>)}</div>
      </div>
    </section>
  );
}

function PrivacyView({ bundle }: { bundle: any }) {
  const records = bundle.records.filter((record: any) => record.slice === "privacy");
  const byExample = Array.from(new Set(records.map((record: any) => record.example_id))) as string[];
  return (
    <section className="view-wrap privacy-view">
      <div className="section-intro"><div><span className="kicker">SYNTHETIC CANARIES ONLY</span><h1>Measure copying, not guarantees.</h1><p>Every identifier is deliberately fake. Exact and normalized retention reveal observed output behavior.</p></div><span className="safety-badge">No real personal data</span></div>
      <div className="privacy-summary">{bundle.analysis.privacy.map((row: any, index: number) => <article key={row.model_id}><i style={{ background: MODEL_COLORS[index % MODEL_COLORS.length] }} /><div><span>{row.model_label}</span><strong>{formatNumber(row.normalized_copy_rate * 100, 0)}%</strong><small>normalized copy · n={row.n}</small></div></article>)}</div>
      <div className="canary-list">{byExample.map((id, index) => { const grouped = records.filter((record: any) => record.example_id === id); return <article className="canary-card" key={id}><div className="canary-source"><span className="canary-index">C{String(index + 1).padStart(2, "0")}</span><div><span className="eyebrow">{grouped[0].title}</span><p>{grouped[0].source}</p></div></div><div className="canary-results">{grouped.map((record: any) => <div key={record.model_id}><span>{record.model_label}</span><p>{record.output}</p><b className={record.privacy.normalized_copy ? "copied" : "clear"}>{record.privacy.normalized_copy ? "CANARY RETAINED" : "CANARY OMITTED"}</b></div>)}</div></article>; })}</div>
      <div className="boundary-note"><strong>Interpretation boundary</strong><p>Passing three synthetic prompts does not establish resistance to memorization, extraction, reconstruction, or attacks. This slice measures direct copying in these exact outputs only.</p></div>
    </section>
  );
}

function ReviewView({ bundle, reviewIndex, setReviewIndex, choices, setChoices, reasons, setReasons, reviewerId, setReviewerId }: any) {
  const cards = bundle.analysis.human_review.cards ?? [];
  const card = cards[reviewIndex % Math.max(1, cards.length)];
  const choice = card ? choices[card.card_id] : undefined;
  const reason = card ? reasons[card.card_id] : undefined;
  const completedCardIds = Object.keys(choices).filter((cardId) => reasons[cardId]);
  const select = (next: Choice) => setChoices({ ...choices, [card.card_id]: next });
  const exportRatings = () => {
    const escape = (value: string) => `"${String(value).replaceAll('"', '""')}"`;
    const exportable = completedCardIds.map((cardId) => cards.find((item: any) => item.card_id === cardId)).filter(Boolean);
    const correctedHeader = "review_id,card_id,example_id,left_blind_id,right_blind_id,choice,reason_tag,reviewer_id\n";
    const rows = exportable.map((item: any, index: number) => [
      `local-${index + 1}`, item.card_id, item.example_id, "A", "B",
      choices[item.card_id], reasons[item.card_id], reviewerId,
    ].map(escape).join(",")).join("\n");
    const correctedBlob = new Blob([correctedHeader + rows + "\n"], { type: "text/csv" });
    const correctedUrl = URL.createObjectURL(correctedBlob);
    const anchor = document.createElement("a");
    anchor.href = correctedUrl;
    anchor.download = "privateeval-blinded-ratings.csv";
    anchor.click();
    URL.revokeObjectURL(correctedUrl);
  };
  if (!card) return <section className="view-wrap"><EmptyState title="Review packet unavailable" detail="Generate a fixed review packet from the measured bundle first." /></section>;
  return (
    <section className="view-wrap review-view">
      <div className="section-intro"><div><span className="kicker">FIXED 12-CARD REVIEW PACKET</span><h1>Judge the output, not the label.</h1><p>Model identities stay hidden. Every judgment requires a rubric reason before it can be exported.</p></div><div className="review-progress"><strong>{completedCardIds.length}</strong><span>/ {bundle.analysis.human_review.target} annotated</span></div></div>
      <div className="review-source"><span className="eyebrow">{card.card_id} · SOURCE · {card.topic.replaceAll("_", " ")}</span><h2>{card.title}</h2><p>{card.source}</p></div>
      <div className="blind-grid"><article><span className="blind-label">A</span><p>{card.output_a || <em>Empty output</em>}</p><button className={choice === "A" ? "selected" : ""} onClick={() => select("A")}>Prefer A</button></article><article><span className="blind-label">B</span><p>{card.output_b || <em>Empty output</em>}</p><button className={choice === "B" ? "selected" : ""} onClick={() => select("B")}>Prefer B</button></article></div>
      <div className="review-controls"><div className="review-judgment"><button className={choice === "Tie" ? "tie-button selected" : "tie-button"} onClick={() => select("Tie")}>Mark as tie</button><label><span>Required reason</span><select value={reason ?? ""} onChange={(event) => setReasons({ ...reasons, [card.card_id]: event.target.value })}><option value="" disabled>Select rubric tag</option><option value="unsupported">Unsupported claim</option><option value="missed-main-point">Missed main point</option><option value="too-long">Too long</option><option value="too-vague">Too vague</option><option value="repetition">Repetition</option><option value="privacy-copy">Privacy copy</option><option value="equivalent">Equivalent</option></select></label></div><div><button className="ghost-button" onClick={() => setReviewIndex((reviewIndex - 1 + cards.length) % cards.length)}>← Previous</button><button className="primary-button" onClick={() => setReviewIndex((reviewIndex + 1) % cards.length)}>Next card →</button></div></div>
      {bundle.analysis.human_review.comparisons?.length > 0 && <div className="preference-results"><span className="eyebrow">OFFICIAL UNBLINDED RESULTS</span>{bundle.analysis.human_review.comparisons.map((comparison: any) => <p key={`${comparison.left_model_id}-${comparison.right_model_id}`}><strong>{comparison.left_model_label}</strong> preference {formatNumber(comparison.left_preference_rate * 100, 1)}% <small>95% CI {formatNumber(comparison.low * 100, 1)}–{formatNumber(comparison.high * 100, 1)}%, n={comparison.n}, versus {comparison.right_model_label}</small></p>)}</div>}
      <div className="export-strip"><div><strong>Keep the evidence honest</strong><p>{bundle.analysis.human_review.completed} official cards are currently in the bundle. Local choices remain working notes until imported and rerun.</p></div><label className="reviewer-id"><span>Reviewer ID</span><input value={reviewerId} onChange={(event) => setReviewerId(event.target.value)} aria-label="Reviewer ID" /></label><button disabled={!completedCardIds.length || !reviewerId.trim()} onClick={exportRatings}>Export {completedCardIds.length} ratings ↓</button></div>
    </section>
  );
}

function MethodView({ bundle }: { bundle: any }) {
  const comparison = bundle.analysis.primary_comparison;
  const [copied, setCopied] = useState(false);
  const reproductionCommand = "python -m privateeval run --config configs/demo.json --output artifacts/runs/reproduction";
  const aggregateById = new Map(bundle.aggregates.models.map((model: any) => [model.model_id, model]));
  const copyReproductionCommand = async () => {
    await navigator.clipboard.writeText(reproductionCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };
  return (
    <section className="view-wrap method-view">
      <div className="section-intro"><div><span className="kicker">METHOD / PROVENANCE / LIMITS</span><h1>The fine print is part of the result.</h1><p>Protocol choices were frozen before the measured run, and every missing evidence item stays visible.</p></div><span className="schema-chip">schema {bundle.schema_version}</span></div>
      <div className="method-grid"><article className="protocol-card"><span className="eyebrow">REGISTERED PROTOCOL</span><h2>{bundle.run.id}</h2><dl><div><dt>Dataset</dt><dd>{bundle.protocol.dataset.id}<small>{bundle.protocol.dataset.split} · {bundle.protocol.dataset.license}</small></dd></div><div><dt>Primary metric</dt><dd>{bundle.protocol.primary_metric}<small>{bundle.protocol.semantic_metric}</small></dd></div><div><dt>Uncertainty</dt><dd>{bundle.protocol.bootstrap_samples.toLocaleString()} paired resamples<small>{bundle.protocol.confidence_level * 100}% percentile interval</small></dd></div><div><dt>Input boundary</dt><dd>{bundle.protocol.input_word_limit} words<small>target {bundle.protocol.target_output_words.join("–")} output words</small></dd></div></dl></article><article className="environment-card"><span className="eyebrow">RECORDED ENVIRONMENT</span><h2>{bundle.environment.hardware_label}</h2><dl><div><dt>Processor</dt><dd>{bundle.environment.processor}</dd></div><div><dt>Logical CPUs</dt><dd>{bundle.environment.logical_cpu_count}</dd></div><div><dt>System memory</dt><dd>{bundle.environment.memory_gb ? `${bundle.environment.memory_gb} GB` : "not recorded"}</dd></div><div><dt>Python</dt><dd>{bundle.environment.python}</dd></div></dl><p>No Apple Silicon measurement is claimed from this run.</p></article></div>
      {comparison && <article className="comparison-callout"><span className="eyebrow">REGISTERED PAIRED CONTRAST</span><div><strong>{comparison.left_model_id}</strong><span>minus</span><strong>{comparison.right_model_id}</strong></div><h2>{comparison.difference > 0 ? "+" : ""}{formatNumber(comparison.difference, 3)} <small>95% CI {formatNumber(comparison.low, 3)} to {formatNumber(comparison.high, 3)}</small></h2><p>Paired dz {formatNumber(comparison.effect_size_dz, 2)} · common-language probability {formatNumber(comparison.common_language_probability * 100, 0)}% · n={comparison.n}</p></article>}
      <div className="status-ledger">
        <article><span className="status-icon done">✓</span><div><strong>Checksums & leakage guard</strong><p>{bundle.validation.verified_files.length} frozen artifacts verified; no adaptation/test overlap.</p></div></article>
        <article><span className={cx("status-icon", bundle.analysis.human_review.status === "complete" ? "done" : "pending")}>{bundle.analysis.human_review.status === "complete" ? "✓" : "…"}</span><div><strong>Blinded human review</strong><p>{bundle.analysis.human_review.completed} of {bundle.analysis.human_review.target} official ratings complete; {bundle.analysis.human_review.cards_available} fixed cards available.</p></div></article>
        <article><span className="status-icon pending">…</span><div><strong>Independent reproduction</strong><p>{bundle.run.independent_verification}. A separate reviewer must rerun the core experiment.</p></div></article>
        <article><span className="status-icon done">✓</span><div><strong>Public repository</strong><p><a href="https://github.com/ArmanM1/privateeval" target="_blank" rel="noreferrer">github.com/ArmanM1/privateeval</a> · public and versioned.</p></div></article>
      </div>
      <div className="configuration-section">
        <div className="panel-heading"><div><span className="eyebrow">CONFIGURATION CARDS</span><h2>Exact systems behind this run</h2></div><span className="panel-meta">pinned and traceable</span></div>
        <div className="configuration-grid">{bundle.config.models.map((model: any, index: number) => { const aggregate = aggregateById.get(model.id) as any; return <article key={model.id}><span className="configuration-number">{String(index + 1).padStart(2, "0")}</span><span className="eyebrow">{model.kind.replaceAll("_", " ")}</span><h3>{model.label}</h3><dl><div><dt>Checkpoint</dt><dd>{model.model_name ?? "deterministic local algorithm"}</dd></div><div><dt>Revision</dt><dd>{model.revision ?? "repository source"}</dd></div><div><dt>Quantization</dt><dd>{model.quantization ?? "none"}</dd></div><div><dt>Semantic score</dt><dd>{formatNumber(aggregate?.quality.semantic_similarity.mean, 3)}</dd></div><div><dt>Warm latency</dt><dd>{formatLatency(aggregate?.efficiency.median_latency_ms)}</dd></div></dl></article>; })}</div>
      </div>
      <article className="reproduction-panel">
        <div><span className="eyebrow">ONE-COMMAND REPRODUCTION</span><h2>Re-run the selected registered evaluation.</h2><p>From a clean checkout after installing the lockfile. The command validates the frozen manifest and writes a new machine-specific result bundle.</p></div>
        <div className="reproduction-command"><code>{reproductionCommand}</code><button onClick={copyReproductionCommand}>{copied ? "Copied" : "Copy command"}</button></div>
        <p className="artifact-paths"><strong>Audit trail:</strong> <code>reports/MODEL_CARD.md</code> · <code>docs/experiment-registration.md</code> · <code>configs/demo.json</code> · <code>public/results/result_bundle.json</code></p>
      </article>
      <div className="limitations-panel"><div><span className="eyebrow">THREATS TO VALIDITY</span><h2>What this run cannot establish</h2></div><ol>{bundle.limitations.map((item: string, index: number) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span>{item}</li>)}</ol></div>
    </section>
  );
}
