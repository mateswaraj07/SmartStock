import { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "./api";

// ---------- toast (call toast("msg") or toast("msg","danger") from anywhere)
export const toast = (msg, type = "success") => window.dispatchEvent(new CustomEvent("toast", { detail: { msg, type } }));
export function ToastHost() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    const h = (e) => {
      const id = Math.random();
      setItems((x) => [...x, { id, ...e.detail }]);
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4000);
    };
    window.addEventListener("toast", h);
    return () => window.removeEventListener("toast", h);
  }, []);
  return (
    <div className="toast-container position-fixed top-0 end-0 p-3" style={{ zIndex: 2000 }}>
      {items.map((i) => (
        <div key={i.id} className={`toast show text-bg-${i.type} mb-2`}><div className="toast-body">{i.msg}</div></div>
      ))}
    </div>
  );
}

// run an API call, show a toast with the result, then refresh
export async function act(fn, ok = "Done", after) {
  try {
    await fn();
    toast(ok);
    after && after();
  } catch (e) {
    toast(errMsg(e), "danger");
  }
}

// ---------- data hook
export function useFetch(url, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(() => {
    api.get(url).then((r) => { setData(r.data); setError(null); }).catch((e) => setError(errMsg(e)));
  }, [url]);
  useEffect(load, [load, ...deps]);
  return { data, error, reload: load };
}

export const Loading = () => <div className="text-center p-5"><div className="spinner-border text-primary" /></div>;
export const Empty = ({ text = "Nothing here yet." }) => <div className="text-center text-muted p-4"><i className="bi bi-inbox fs-1 d-block" />{text}</div>;
export const ErrorBox = ({ msg }) => <div className="alert alert-danger">{msg}</div>;
export function Async({ res, children }) {
  if (res.error) return <ErrorBox msg={res.error} />;
  if (!res.data) return <Loading />;
  return children(res.data);
}

const COLORS = {
  PENDING: "warning text-dark", ACCEPTED: "info text-dark", REJECTED: "danger", PREPARING: "info text-dark", READY: "primary",
  OUT_FOR_DELIVERY: "primary", DELIVERED: "success", CANCELLED: "secondary", FAILED: "danger", ASSIGNED: "info text-dark",
  ACTIVE: "success", AVAILABLE: "secondary", EMPTY: "dark", INACTIVE: "secondary", LOW: "warning text-dark", CRITICAL: "danger",
  OK: "success", DISPATCHED: "primary", RECEIVED: "success", PAID: "success", UNPAID: "warning text-dark",
  PARTIAL: "info text-dark", NOT_BILLED: "secondary", ACTION: "warning text-dark", INFO: "info text-dark", PAYMENT: "primary", SALE: "primary", STOCK_RECEIVED: "success", STOCK_ADJUSTMENT: "warning text-dark", BAG_ACTIVATED: "info text-dark", BAG_EMPTY: "dark",
};
export const Badge = ({ s }) => <span className={`badge bg-${COLORS[s] || "secondary"}`}>{String(s).replace(/_/g, " ")}</span>;
export const money = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
export const qty = (n) => Number(n).toString();
export const when = (d) => (d ? new Date(d).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "-");

export const Stat = ({ label, value, icon = "bi-graph-up", tone = "primary" }) => (
  <div className="col-6 col-md-4 col-xl-3"><div className="card stat h-100"><div className="card-body d-flex justify-content-between align-items-center">
    <div><div className="text-muted small">{label}</div><div className="num">{value}</div></div>
    <i className={`bi ${icon} fs-2 text-${tone}`} />
  </div></div></div>
);

export function Modal({ title, onClose, children, size = "" }) {
  return (
    <div className="modal-backdrop-lite" onClick={onClose}>
      <div className={`modal-dialog modal-dialog-centered ${size}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-content">
          <div className="modal-header"><h5 className="modal-title">{title}</h5><button className="btn-close" onClick={onClose} /></div>
          <div className="modal-body">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function Confirm({ text, onYes, onClose }) {
  return (
    <Modal title="Please confirm" onClose={onClose}>
      <p>{text}</p>
      <div className="text-end"><button className="btn btn-light me-2" onClick={onClose}>No</button>
        <button className="btn btn-danger" onClick={() => { onYes(); onClose(); }}>Yes</button></div>
    </Modal>
  );
}

export const Field = ({ label, children }) => <div className="mb-3"><label className="form-label small fw-semibold">{label}</label>{children}</div>;
export const Table = ({ head, children }) => (
  <div className="table-responsive"><table className="table table-hover align-middle mb-0">
    <thead className="table-light"><tr>{head.map((h) => <th key={h} className="text-nowrap">{h}</th>)}</tr></thead>
    <tbody>{children}</tbody></table></div>
);
export const Page = ({ title, actions, children }) => (
  <div><div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2"><h4 className="mb-0">{title}</h4><div>{actions}</div></div>{children}</div>
);
