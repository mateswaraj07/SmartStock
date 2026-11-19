import { Async, Badge, Empty, Page, useFetch } from "../ui";

export function AlertsPage() {
  const res = useFetch("/alerts/");
  return (
    <Page title="Alerts" actions={<span className="text-muted small">Built from your live stock, requests and payments</span>}>
      <Async res={res}>{({ results }) => results.length ? (
        <div className="list-group">{results.map((a, i) => (
          <div key={i} className="list-group-item d-flex gap-3 align-items-start">
            <Badge s={a.type} /><div><div className="fw-semibold">{a.title}</div><div className="text-muted small">{a.message}</div></div></div>))}</div>
      ) : <Empty text="Nothing needs your attention." />}</Async>
    </Page>
  );
}
