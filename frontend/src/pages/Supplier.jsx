import { useState } from "react";
import { api } from "../api";
import { act, Async, Badge, Empty, Field, Modal, money, Page, qty, Stat, Table, useFetch, when } from "../ui";

export function SupplierPage() {
  const [tab, setTab] = useState("Requests");
  const [status, setStatus] = useState("");
  const res = useFetch("/reorders/" + (status ? `?status=${status}` : ""), [status]);
  const all = useFetch("/reorders/");
  const pays = useFetch("/payments/");
  const sum = useFetch("/payments/summary/");
  const [dlg, setDlg] = useState(null); // {req, action}
  const [f, setF] = useState({});
  const reload = () => { res.reload(); all.reload(); pays.reload(); sum.reload(); setDlg(null); };
  const run = (req, action, body = {}) => act(() => api.post(`/reorders/${req.id}/${action}/`, body), "Updated", reload);
  const count = (s) => all.data?.filter((r) => r.status === s).length ?? 0;
  return (
    <Page title="Supply requests & payments">
      <div className="row g-3 mb-3">
        <Stat label="Pending" value={count("PENDING")} icon="bi-hourglass" tone="warning" />
        <Stat label="Accepted" value={count("ACCEPTED")} icon="bi-check2" />
        <Stat label="Dispatched" value={count("DISPATCHED")} icon="bi-truck" />
        <Stat label="Delivered" value={count("DELIVERED")} icon="bi-box-seam" />
        <Stat label="Completed" value={count("RECEIVED")} icon="bi-patch-check" tone="success" />
        <Stat label="Rejected" value={count("REJECTED")} icon="bi-x-circle" tone="danger" />
      </div>
      <Async res={sum}>{(s) => (
        <div className="row g-3 mb-3">
          <Stat label="Total billed" value={money(s.billed)} icon="bi-receipt" />
          <Stat label="Received" value={money(s.paid)} icon="bi-cash-coin" tone="success" />
          <Stat label="Balance receivable" value={money(s.due)} icon="bi-exclamation-circle" tone="danger" />
          <Stat label="Payments to confirm" value={s.unconfirmed} icon="bi-hourglass" tone="warning" />
        </div>)}</Async>
      <ul className="nav nav-pills mb-3">{["Requests", "Payments"].map((t) => <li key={t} className="nav-item"><button className={`nav-link ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</button></li>)}</ul>

      {tab === "Requests" && <>
        <select className="form-select mb-3" style={{ maxWidth: 240 }} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All requests</option>{["PENDING", "ACCEPTED", "DISPATCHED", "DELIVERED", "RECEIVED", "REJECTED"].map((s) => <option key={s}>{s}</option>)}</select>
        <div className="card"><Async res={res}>{(list) => list.length ? (
          <Table head={["Request", "Shop", "Product", "Requested", "Supplied", "Rate", "Status", "Bill", "Payment", "Date", "Action"]}>
            {list.map((r) => (
              <tr key={r.id}><td>{r.request_no}</td><td>{r.shop_name}</td><td>{r.product_name}</td><td>{qty(r.requested_qty)} {r.unit}</td>
                <td>{r.supplied_qty ? `${qty(r.supplied_qty)} ${r.unit}` : "-"}</td><td>{Number(r.unit_rate) ? money(r.unit_rate) : "-"}</td><td><Badge s={r.status} /></td>
                <td>{r.status === "RECEIVED" ? money(r.bill_amount) : "-"}</td><td>{r.payment_status !== "NOT_BILLED" ? <Badge s={r.payment_status} /> : "-"}</td>
                <td className="text-nowrap">{when(r.request_date)}</td>
                <td className="text-nowrap">
                  {r.status === "PENDING" && <><button className="btn btn-sm btn-success me-1" onClick={() => { setF({ unit_rate: r.unit_rate }); setDlg({ req: r, action: "accept" }); }}>Accept</button>
                    <button className="btn btn-sm btn-outline-danger" onClick={() => run(r, "reject")}>Reject</button></>}
                  {r.status === "ACCEPTED" && <button className="btn btn-sm btn-primary" onClick={() => run(r, "dispatch")}>Mark dispatched</button>}
                  {r.status === "DISPATCHED" && <button className="btn btn-sm btn-primary" onClick={() => { setF({ supplied_qty: r.requested_qty }); setDlg({ req: r, action: "deliver" }); }}>Mark delivered</button>}
                  {r.status === "DELIVERED" && <span className="small text-muted">Awaiting shop confirmation</span>}
                </td></tr>))}
          </Table>) : <Empty text="No requests." />}</Async></div></>}

      {tab === "Payments" && <>
        <div className="card"><Async res={pays}>{(l) => l.length ? (
          <Table head={["Payment", "Date", "Shop", "Request", "Product", "Amount paid", "Balance remaining", "Method", "Reference", "Status", ""]}>
            {l.map((p) => <tr key={p.id}><td><b>{p.payment_no}</b></td><td className="text-nowrap">{when(p.payment_date)}</td><td>{p.shop_name}</td><td>{p.request_no}</td><td>{p.product_name}</td>
              <td>{money(p.amount_paid)}</td><td>{money(p.balance_remaining)}</td><td>{p.payment_method.replace("_", " ")}</td><td>{p.reference_no || "-"}</td>
              <td><Badge s={p.supplier_confirmed ? "PAID" : "PENDING"} /></td>
              <td>{!p.supplier_confirmed && <button className="btn btn-sm btn-success text-nowrap" onClick={() => act(() => api.post(`/payments/${p.id}/confirm/`), "Payment confirmed", reload)}>Confirm received</button>}</td></tr>)}
          </Table>) : <Empty text="No payments yet. They appear after a shop receives your delivery and pays the bill." />}</Async></div>
        <Async res={sum}>{(s) => s.by_party.length > 0 && (
          <div className="card mt-3"><div className="card-header bg-white fw-semibold">Balance receivable by shop</div>
            <Table head={["Shop", "Billed", "Received", "Balance remaining"]}>{s.by_party.map((x) => <tr key={x.name}><td>{x.name}</td><td>{money(x.billed)}</td><td>{money(x.paid)}</td><td className={Number(x.due) > 0 ? "text-danger fw-bold" : ""}>{money(x.due)}</td></tr>)}</Table></div>)}</Async></>}

      {dlg && (
        <Modal title={`${dlg.action === "accept" ? "Accept request" : "Delivery details"} · ${dlg.req.request_no}`} onClose={() => setDlg(null)}>
          <p className="small">{dlg.req.shop_name} · {dlg.req.product_name} · requested {qty(dlg.req.requested_qty)} {dlg.req.unit}</p>
          {dlg.action === "accept" && <Field label={`Your rate (₹ per ${dlg.req.unit}): the shop is billed at this rate`}><input type="number" step="0.01" className="form-control" value={f.unit_rate} onChange={(e) => setF({ ...f, unit_rate: e.target.value })} /></Field>}
          {dlg.action === "deliver" && <Field label={`Supplied quantity (requested ${qty(dlg.req.requested_qty)} ${dlg.req.unit})`}><input type="number" step="0.001" className="form-control" value={f.supplied_qty} onChange={(e) => setF({ ...f, supplied_qty: e.target.value })} /></Field>}
          <div className="small text-muted mb-2">Stock is added to the shop only after the owner confirms the received quantity. The bill is created at that point.</div>
          <button className="btn btn-primary" onClick={() => run(dlg.req, dlg.action, f)}>Confirm</button>
        </Modal>)}
    </Page>
  );
}
