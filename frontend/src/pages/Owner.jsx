import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, download } from "../api";
import { act, Async, Badge, Confirm, Empty, Field, Modal, money, Page, qty, Stat, Table, useFetch, when } from "../ui";

const Tabs = ({ tabs, value, onChange }) => (
  <ul className="nav nav-pills mb-3 flex-nowrap overflow-auto">{tabs.map((t) => (
    <li key={t} className="nav-item"><button className={`nav-link text-nowrap ${value === t ? "active" : ""}`} onClick={() => onChange(t)}>{t}</button></li>))}</ul>
);
const Chart = ({ children, h = 240 }) => <div style={{ width: "100%", height: h }}><ResponsiveContainer>{children}</ResponsiveContainer></div>;
const n = (v) => Number(v);

// ============================================================ DASHBOARD
export function OwnerDashboard() {
  const [days, setDays] = useState("30");
  const res = useFetch(`/reports/dashboard/?days=${days}`, [days]);
  return (
    <Page title="Dashboard" actions={<select className="form-select form-select-sm" value={days} onChange={(e) => setDays(e.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option></select>}>
      <Async res={res}>{(d) => (
        <>
          <div className="row g-3 mb-3">
            <Stat label="Products" value={d.cards.total_products} icon="bi-boxes" />
            <Stat label="Low / critical stock" value={d.cards.low_stock} icon="bi-exclamation-triangle" tone="danger" />
            <Stat label="Open supplier requests" value={d.cards.open_requests} icon="bi-arrow-repeat" />
            <Stat label="Waiting for your receipt" value={d.cards.awaiting_receipt} icon="bi-box-seam" tone="warning" />
            <Stat label="Billed by suppliers" value={money(d.cards.billed)} icon="bi-receipt" />
            <Stat label="Paid" value={money(d.cards.paid)} icon="bi-check2-circle" tone="success" />
            <Stat label="Balance due" value={money(d.cards.due)} icon="bi-cash-coin" tone="danger" />
          </div>
          <div className="row g-3">
            <div className="col-12 col-lg-6"><div className="card card-body"><h6>Stock received per day</h6>
              <Chart><BarChart data={d.series.map((x) => ({ ...x, received_qty: n(x.received_qty) }))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis /><Tooltip /><Bar dataKey="received_qty" name="Quantity" fill="#198754" /></BarChart></Chart></div></div>
            <div className="col-12 col-lg-6"><div className="card card-body"><h6>Payments to suppliers per day (₹)</h6>
              <Chart><LineChart data={d.series.map((x) => ({ ...x, paid: n(x.paid) }))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis /><Tooltip /><Line dataKey="paid" name="Paid" stroke="#0d6efd" strokeWidth={2} /></LineChart></Chart></div></div>
            <div className="col-12 col-lg-6"><div className="card card-body"><h6>Billed vs paid by supplier (₹)</h6>
              {d.suppliers.length ? <Chart><BarChart data={d.suppliers.map((s) => ({ ...s, billed: n(s.billed), paid: n(s.paid) }))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /><Bar dataKey="billed" fill="#6c757d" /><Bar dataKey="paid" fill="#198754" /></BarChart></Chart> : <Empty text="No supplier bills yet." />}</div></div>
            <div className="col-12 col-lg-6"><div className="card"><div className="card-header bg-white fw-semibold">Low / critical stock</div>
              {d.low_stock_products.length ? <Table head={["Product", "Stock", "Minimum", "Level"]}>{d.low_stock_products.map((p) => <tr key={p.id}><td>{p.name}</td><td>{qty(p.stock)} {p.unit}</td><td>{qty(p.min)}</td><td><Badge s={p.level} /></td></tr>)}</Table> : <Empty text="All products are sufficiently stocked." />}</div></div>
          </div>
        </>)}</Async>
    </Page>
  );
}

// ============================================================ PRODUCTS
function ProductForm({ product, onClose, onSaved }) {
  const cats = useFetch("/masters/?type=PRODUCT_CATEGORY");
  const units = useFetch("/masters/?type=UNIT");
  const sups = useFetch("/suppliers/");
  const [f, setF] = useState({ product_name: "", category: "", selling_price: "", cost_price: 0, unit: "KG", min_stock: 0, reorder_qty: 0, supplier: "", ...(product || {}) });
  const [newCat, setNewCat] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = () => {
    const body = { product_name: f.product_name, category: f.category || null, selling_price: f.selling_price, cost_price: f.cost_price, unit: f.unit, min_stock: f.min_stock, reorder_qty: f.reorder_qty, supplier: f.supplier || null };
    act(() => (product ? api.patch(`/products/${product.id}/`, body) : api.post("/products/", body)), "Product saved", onSaved);
  };
  const addCat = () => act(async () => { const r = await api.post("/masters/", { master_value: newCat }); setF({ ...f, category: r.data.id }); setNewCat(""); cats.reload(); }, "Category added");
  return (
    <Modal title={product ? "Edit product" : "Add product"} onClose={onClose}>
      <div className="row">
        <div className="col-12"><Field label="Product name"><input className="form-control" value={f.product_name} onChange={set("product_name")} /></Field></div>
        <div className="col-6"><Field label="Category"><select className="form-select" value={f.category || ""} onChange={set("category")}><option value="">-</option>{cats.data?.map((c) => <option key={c.id} value={c.id}>{c.master_value}</option>)}</select></Field></div>
        <div className="col-6"><Field label="New category"><div className="input-group"><input className="form-control" value={newCat} onChange={(e) => setNewCat(e.target.value)} /><button className="btn btn-outline-secondary" disabled={!newCat} onClick={addCat}>Add</button></div></Field></div>
        <div className="col-6"><Field label="Selling price (₹)"><input type="number" step="0.01" className="form-control" value={f.selling_price} onChange={set("selling_price")} /></Field></div>
        <div className="col-6"><Field label="Supplier cost price (₹ per unit)"><input type="number" step="0.01" className="form-control" value={f.cost_price} onChange={set("cost_price")} /></Field></div>
        <div className="col-4"><Field label="Unit"><select className="form-select" value={f.unit} onChange={set("unit")}>{units.data?.map((u) => <option key={u.id} value={u.master_code}>{u.master_value}</option>)}</select></Field></div>
        <div className="col-4"><Field label="Minimum stock"><input type="number" step="0.001" className="form-control" value={f.min_stock} onChange={set("min_stock")} /></Field></div>
        <div className="col-4"><Field label="Reorder quantity"><input type="number" step="0.001" className="form-control" value={f.reorder_qty} onChange={set("reorder_qty")} /></Field></div>
        <div className="col-12"><Field label="Supplier"><select className="form-select" value={f.supplier || ""} onChange={set("supplier")}><option value="">-</option>{sups.data?.map((s) => <option key={s.id} value={s.id}>{s.company_name}</option>)}</select></Field></div>
      </div>
      <button className="btn btn-primary" onClick={save}>Save</button>
    </Modal>
  );
}

export function OwnerProducts() {
  const [q, setQ] = useState("");
  const res = useFetch("/products/?search=" + encodeURIComponent(q), [q]);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  return (
    <Page title="Products" actions={<button className="btn btn-primary" onClick={() => setEdit({})}><i className="bi bi-plus-lg" /> Add product</button>}>
      <input className="form-control mb-3" placeholder="Search product or Bag ID" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card"><Async res={res}>{(list) => list.length ? (
        <Table head={["Product", "Category", "Price", "Cost", "Stock", "Min", "Supplier", "Status", ""]}>
          {list.map((p) => (
            <tr key={p.id}><td><b>{p.product_name}</b></td><td>{p.category_name}</td><td>{money(p.selling_price)}/{p.unit}</td><td>{money(p.cost_price)}</td>
              <td>{qty(p.total_stock)} {p.unit} <Badge s={p.stock_status} /></td><td>{qty(p.min_stock)}</td><td>{p.supplier_name}</td><td><Badge s={p.is_active ? "ACTIVE" : "INACTIVE"} /></td>
              <td className="text-nowrap"><button className="btn btn-sm btn-outline-primary me-1" onClick={() => setEdit(p)}>Edit</button>
                {p.is_active ? <button className="btn btn-sm btn-outline-danger" onClick={() => setDel(p)}>Deactivate</button>
                  : <button className="btn btn-sm btn-outline-success" onClick={() => act(() => api.patch(`/products/${p.id}/`, { is_active: true }), "Activated", res.reload)}>Activate</button>}</td></tr>))}
        </Table>) : <Empty text="No products yet." />}</Async></div>
      {edit && <ProductForm product={edit.id ? edit : null} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); res.reload(); }} />}
      {del && <Confirm text={`Deactivate ${del.product_name}? Its history is kept.`} onClose={() => setDel(null)} onYes={() => act(() => api.delete(`/products/${del.id}/`), "Deactivated", res.reload)} />}
    </Page>
  );
}

// ============================================================ STOCK
const REASONS = ["DAMAGE", "WASTAGE", "EXPIRED", "COUNT_DIFFERENCE", "CORRECTION", "OTHER"];
export function OwnerStock() {
  const [tab, setTab] = useState("Bags");
  const bags = useFetch("/bags/");
  const hist = useFetch("/stock-history/");
  const prods = useFetch("/products/");
  const [dlg, setDlg] = useState(null);
  const [f, setF] = useState({ product: "", quantity: "", reason: "DAMAGE", remarks: "" });
  const reload = () => { bags.reload(); hist.reload(); prods.reload(); setDlg(null); };
  const submit = () => act(() => (dlg === "bag" ? api.post("/bags/", { product: f.product, quantity: f.quantity })
    : api.post("/stock/adjust/", { ...f, quantity: dlg === "remove" ? -Math.abs(f.quantity) : Math.abs(f.quantity) })), "Saved", reload);
  return (
    <Page title="Stock" actions={<div className="d-flex gap-2">
      <button className="btn btn-outline-primary btn-sm" onClick={() => setDlg("bag")}>+ Opening bag</button>
      <button className="btn btn-outline-danger btn-sm" onClick={() => setDlg("remove")}>Adjust stock</button></div>}>
      <Tabs tabs={["Bags", "Stock history", "Products"]} value={tab} onChange={setTab} />
      <div className="card">
        {tab === "Bags" && <Async res={bags}>{(l) => l.length ? <Table head={["Bag ID", "Product", "Initial", "Current", "Status"]}>
          {l.map((b) => <tr key={b.id}><td><b>{b.bag_code}</b></td><td>{b.product_name}</td><td>{qty(b.initial_qty)} {b.unit}</td><td>{qty(b.current_qty)} {b.unit}</td><td><Badge s={b.status} /></td></tr>)}</Table> : <Empty />}</Async>}
        {tab === "Stock history" && <Async res={hist}>{(l) => l.length ? <Table head={["Date", "Product", "Bag", "Type", "Quantity", "Before", "After", "Remarks"]}>
          {l.map((t) => <tr key={t.id}><td className="text-nowrap">{when(t.txn_date)}</td><td>{t.product_name}</td><td>{t.bag_code}</td><td><Badge s={t.txn_type} /></td>
            <td className={n(t.quantity) < 0 ? "text-danger" : "text-success"}>{n(t.quantity) > 0 ? "+" : ""}{qty(t.quantity)}</td><td>{qty(t.qty_before)}</td><td>{qty(t.qty_after)}</td><td>{t.remarks}</td></tr>)}</Table> : <Empty />}</Async>}
        {tab === "Products" && <Async res={prods}>{(l) => <Table head={["Product", "Stock", "Minimum", "Level"]}>
          {l.filter((p) => p.is_active).map((p) => <tr key={p.id}><td>{p.product_name}</td><td>{qty(p.total_stock)} {p.unit}</td><td>{qty(p.min_stock)}</td><td><Badge s={p.stock_status} /></td></tr>)}</Table>}</Async>}
      </div>
      {dlg && (
        <Modal title={dlg === "bag" ? "Add opening bag" : "Stock adjustment"} onClose={() => setDlg(null)}>
          <Field label="Product"><select className="form-select" onChange={(e) => setF({ ...f, product: e.target.value })}><option value="">Select...</option>{prods.data?.filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{p.product_name} ({p.unit})</option>)}</select></Field>
          {dlg !== "bag" && <div className="btn-group mb-3 w-100"><button className={`btn btn-${dlg === "remove" ? "danger" : "outline-danger"}`} onClick={() => setDlg("remove")}>Reduce</button>
            <button className={`btn btn-${dlg === "add" ? "success" : "outline-success"}`} onClick={() => setDlg("add")}>Increase</button></div>}
          <Field label="Quantity"><input type="number" step="0.001" min="0" className="form-control" onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          {dlg !== "bag" && <><Field label="Reason"><select className="form-select" onChange={(e) => setF({ ...f, reason: e.target.value })}>{REASONS.map((r) => <option key={r}>{r}</option>)}</select></Field>
            <Field label="Remarks (required)"><input className="form-control" onChange={(e) => setF({ ...f, remarks: e.target.value })} /></Field></>}
          <div className="small text-muted mb-2">Stock goes up through supplier deliveries you confirm. Use this form only for opening stock and corrections.</div>
          <button className="btn btn-primary" onClick={submit}>Save</button>
        </Modal>)}
    </Page>
  );
}

// ============================================================ REORDERS, RESTOCKED, PAYMENTS
export function OwnerReorders() {
  const [tab, setTab] = useState("Reorder requests");
  const res = useFetch("/reorders/");
  const rest = useFetch("/restocked/");
  const pays = useFetch("/payments/");
  const sum = useFetch("/payments/summary/");
  const prods = useFetch("/products/");
  const methods = useFetch("/masters/?type=PAYMENT_METHOD");
  const [recv, setRecv] = useState(null);
  const [pay, setPay] = useState(null);
  const [create, setCreate] = useState(null);
  const [f, setF] = useState({});
  const reload = () => { res.reload(); rest.reload(); pays.reload(); sum.reload(); prods.reload(); setRecv(null); setPay(null); setCreate(null); };
  return (
    <Page title="Supplier reorders & payments" actions={<button className="btn btn-outline-primary btn-sm" onClick={() => { setF({}); setCreate(true); }}>+ Create reorder request</button>}>
      <Async res={sum}>{(s) => (
        <div className="row g-3 mb-3">
          <Stat label="Billed by suppliers" value={money(s.billed)} icon="bi-receipt" />
          <Stat label="Paid" value={money(s.paid)} icon="bi-check2-circle" tone="success" />
          <Stat label="Balance remaining" value={money(s.due)} icon="bi-exclamation-circle" tone="danger" />
          <Stat label="Awaiting supplier confirmation" value={s.unconfirmed} icon="bi-hourglass" tone="warning" />
        </div>)}</Async>
      <Tabs tabs={["Reorder requests", "Restocked items", "Payments"]} value={tab} onChange={setTab} />
      <div className="card">
        {tab === "Reorder requests" && <Async res={res}>{(l) => l.length ? <Table head={["Request", "Product", "Supplier", "Requested", "Supplied", "Received", "Rate", "Status", "Bill", "Paid", "Payment", ""]}>
          {l.map((r) => <tr key={r.id}><td>{r.request_no}</td><td>{r.product_name}</td><td>{r.supplier_name}</td><td>{qty(r.requested_qty)} {r.unit}</td>
            <td>{r.supplied_qty ? qty(r.supplied_qty) : "-"}</td><td>{r.received_qty ? qty(r.received_qty) : "-"}</td><td>{money(r.unit_rate)}</td><td><Badge s={r.status} /></td>
            <td>{r.status === "RECEIVED" ? money(r.bill_amount) : "-"}</td><td>{r.status === "RECEIVED" ? money(r.amount_paid) : "-"}</td>
            <td>{r.payment_status !== "NOT_BILLED" ? <Badge s={r.payment_status} /> : "-"}</td>
            <td className="text-nowrap">
              {r.status === "DELIVERED" && <button className="btn btn-sm btn-success" onClick={() => { setF({ received_qty: r.supplied_qty }); setRecv(r); }}>Confirm received</button>}
              {r.status === "RECEIVED" && n(r.due_amount) > 0 && <button className="btn btn-sm btn-primary" onClick={() => { setF({ amount: r.due_amount, payment_method: "CASH", reference_no: "" }); setPay(r); }}>Pay supplier</button>}
            </td></tr>)}</Table> : <Empty text="No reorder requests. They are created automatically when stock is low." />}</Async>}
        {tab === "Restocked items" && <Async res={rest}>{(l) => l.length ? <Table head={["Product", "Supplier", "Requested", "Received", "Stock before", "Stock after", "Received on", "Status"]}>
          {l.map((r) => <tr key={r.id}><td>{r.product_name}</td><td>{r.supplier_name}</td><td>{qty(r.requested_qty)}</td><td className="text-success">+{qty(r.received_qty)} {r.unit}</td>
            <td>{r.qty_before != null ? qty(r.qty_before) : "-"}</td><td>{r.qty_after != null ? qty(r.qty_after) : "-"}</td><td>{when(r.received_on)}</td><td><Badge s={r.status} /></td></tr>)}</Table> : <Empty text="Nothing restocked yet." />}</Async>}
        {tab === "Payments" && <Async res={pays}>{(l) => l.length ? <Table head={["Payment", "Date", "Supplier", "Request", "Product", "Amount paid", "Balance remaining", "Method", "Reference", "Supplier confirmed"]}>
          {l.map((p) => <tr key={p.id}><td><b>{p.payment_no}</b></td><td className="text-nowrap">{when(p.payment_date)}</td><td>{p.supplier_name}</td><td>{p.request_no}</td><td>{p.product_name}</td>
            <td>{money(p.amount_paid)}</td><td className={n(p.balance_remaining) > 0 ? "text-danger" : "text-success"}>{money(p.balance_remaining)}</td>
            <td>{p.payment_method.replace("_", " ")}</td><td>{p.reference_no || "-"}</td><td><Badge s={p.supplier_confirmed ? "PAID" : "PENDING"} /></td></tr>)}</Table> : <Empty text="No payments made yet." />}</Async>}
      </div>
      {tab === "Payments" && <Async res={sum}>{(s) => s.by_party.length > 0 && (
        <div className="card mt-3"><div className="card-header bg-white fw-semibold">Balance by supplier</div>
          <Table head={["Supplier", "Billed", "Paid", "Balance remaining"]}>{s.by_party.map((x) => <tr key={x.name}><td>{x.name}</td><td>{money(x.billed)}</td><td>{money(x.paid)}</td><td className={n(x.due) > 0 ? "text-danger fw-bold" : ""}>{money(x.due)}</td></tr>)}</Table></div>)}</Async>}

      {recv && (
        <Modal title={`Confirm received · ${recv.request_no}`} onClose={() => setRecv(null)}>
          <p>Supplier says <b>{qty(recv.supplied_qty)} {recv.unit}</b> of {recv.product_name} was delivered at <b>{money(recv.unit_rate)}</b> per {recv.unit}. Enter what you actually received. Stock increases and the bill is created only after you confirm.</p>
          <Field label="Actual received quantity"><input type="number" step="0.001" className="form-control" value={f.received_qty} onChange={(e) => setF({ ...f, received_qty: e.target.value })} /></Field>
          <div className="alert alert-info py-2">Bill = {f.received_qty || 0} × {money(recv.unit_rate)} = <b>{money((f.received_qty || 0) * recv.unit_rate)}</b></div>
          <button className="btn btn-success" onClick={() => act(() => api.post(`/reorders/${recv.id}/receive/`, f), "Stock added and bill created", reload)}>Confirm &amp; add to stock</button>
        </Modal>)}
      {pay && (
        <Modal title={`Pay supplier · ${pay.request_no}`} onClose={() => setPay(null)}>
          <p>{pay.supplier_name} · {pay.product_name} · Bill {money(pay.bill_amount)}, paid {money(pay.amount_paid)}, <b className="text-danger">balance {money(pay.due_amount)}</b></p>
          <Field label="Amount (₹), part payment allowed"><input type="number" step="0.01" className="form-control" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field>
          <div className="alert alert-secondary py-2">Balance remaining after this payment: <b>{money(Math.max(0, n(pay.due_amount) - n(f.amount || 0)))}</b></div>
          <Field label="Payment method"><select className="form-select" value={f.payment_method} onChange={(e) => setF({ ...f, payment_method: e.target.value })}>{methods.data?.map((m) => <option key={m.id} value={m.master_code}>{m.master_value}</option>)}</select></Field>
          {f.payment_method !== "CASH" && <Field label="UPI id / transaction no. / cheque no."><input className="form-control" onChange={(e) => setF({ ...f, reference_no: e.target.value })} /></Field>}
          <button className="btn btn-primary" onClick={() => act(() => api.post(`/reorders/${pay.id}/pay/`, f), "Payment recorded", reload)}>Record payment</button>
        </Modal>)}
      {create && (
        <Modal title="Create reorder request" onClose={() => setCreate(null)}>
          <Field label="Product"><select className="form-select" onChange={(e) => setF({ ...f, product: e.target.value })}><option value="">Select...</option>{prods.data?.filter((p) => p.is_active && p.supplier).map((p) => <option key={p.id} value={p.id}>{p.product_name}</option>)}</select></Field>
          <Field label="Quantity (blank = default reorder quantity)"><input type="number" className="form-control" onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          <button className="btn btn-primary" onClick={() => act(() => api.post("/reorders/", f), "Request sent to the supplier", reload)}>Send to supplier</button>
        </Modal>)}
    </Page>
  );
}

// ============================================================ REPORTS
export function OwnerReports() {
  const [kind, setKind] = useState("stock");
  const kinds = [["stock", "Stock"], ["movement", "Stock movement"], ["requests", "Reorder requests"], ["payments", "Supplier payments"]];
  const res = useFetch(`/reports/${kind}/`, [kind]);
  return (
    <Page title="Reports" actions={<button className="btn btn-outline-success btn-sm" onClick={() => download(`/reports/${kind}/?format=csv`, `${kind}-report.csv`)}><i className="bi bi-filetype-csv" /> Export CSV</button>}>
      <Tabs tabs={kinds.map((k) => k[1])} value={kinds.find((k) => k[0] === kind)[1]} onChange={(l) => setKind(kinds.find((k) => k[1] === l)[0])} />
      <div className="card"><Async res={res}>{(d) => d.rows.length ? <Table head={d.headers}>{d.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c ?? "-"}</td>)}</tr>)}</Table> : <Empty text="No data." />}</Async></div>
    </Page>
  );
}
