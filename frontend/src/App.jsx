import { useEffect, useState } from "react";
import { Link, Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import { HOME, useAuth } from "./auth";
import { Login, Register } from "./pages/Auth.jsx";
import { OwnerDashboard, OwnerProducts, OwnerReorders, OwnerReports, OwnerStock } from "./pages/Owner.jsx";
import { AlertsPage } from "./pages/Alerts.jsx";
import { SupplierPage } from "./pages/Supplier.jsx";

const MENU = {
  OWNER: [["/owner", "Dashboard"], ["/owner/products", "Products"], ["/owner/stock", "Stock"], ["/owner/reorders", "Reorders & Payments"], ["/owner/reports", "Reports"]],
  SUPPLIER: [["/supplier", "Requests & Payments"]],
};

function SearchBox() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  useEffect(() => {
    if (q.length < 2) return setRes(null);
    const t = setTimeout(() => api.get("/search/", { params: { q } }).then((r) => setRes(r.data)).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <div className="position-relative me-lg-2 my-2 my-lg-0">
      <input className="form-control form-control-sm" placeholder="Search..." value={q} onChange={(e) => setQ(e.target.value)} />
      {res && (
        <div className="card search-pop p-2 mt-1" onClick={() => setQ("")}>
          {Object.entries(res).filter(([, v]) => v.length).map(([k, rows]) => (
            <div key={k}><div className="small fw-bold text-muted">{k}</div>{rows.map((r, i) => <div key={i} className="small border-bottom py-1">{r}</div>)}</div>
          ))}
          {!Object.values(res).some((v) => v.length) && <div className="small text-muted">No results</div>}
        </div>
      )}
    </div>
  );
}

function Layout({ children }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const nav = useNavigate();
  useEffect(() => {
    const load = () => api.get("/alerts/").then((r) => setCount(r.data.count)).catch(() => {});
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);
  const bell = (
    <Link to="/alerts" className="text-white position-relative"><i className="bi bi-bell fs-5" />
      {count > 0 && <span className="badge bg-danger rounded-pill position-absolute top-0 start-100 translate-middle">{count}</span>}</Link>
  );
  return (
    <>
      <nav className="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
        <div className="container-fluid">
          <Link className="navbar-brand" to={HOME[user.role]}><i className="bi bi-box-seam me-1" />SmartStock</Link>
          <div className="d-flex d-lg-none align-items-center gap-3">{bell}<button className="navbar-toggler" onClick={() => setOpen(!open)}><span className="navbar-toggler-icon" /></button></div>
          <div className={`collapse navbar-collapse ${open ? "show" : ""}`} onClick={() => setOpen(false)}>
            <ul className="navbar-nav me-auto">
              {MENU[user.role].map(([to, label]) => <li key={to} className="nav-item"><NavLink end className="nav-link" to={to}>{label}</NavLink></li>)}
            </ul>
            <div onClick={(e) => e.stopPropagation()}><SearchBox /></div>
            <span className="d-none d-lg-inline mx-3">{bell}</span>
            <span className="btn btn-sm btn-light me-2 disabled">{user.name}</span>
            <button className="btn btn-sm btn-outline-light" onClick={() => { logout(); nav("/login"); }}>Logout</button>
          </div>
        </div>
      </nav>
      <div className="container-fluid py-3" style={{ maxWidth: 1250 }}>{children}</div>
    </>
  );
}

function Guard({ role, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to={HOME[user.role]} replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  const { user } = useAuth();
  const G = (role, el) => <Guard role={role}>{el}</Guard>;
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={HOME[user.role]} /> : <Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Navigate to={user ? HOME[user.role] : "/login"} />} />
      <Route path="/owner" element={G("OWNER", <OwnerDashboard />)} />
      <Route path="/owner/products" element={G("OWNER", <OwnerProducts />)} />
      <Route path="/owner/stock" element={G("OWNER", <OwnerStock />)} />
      <Route path="/owner/reorders" element={G("OWNER", <OwnerReorders />)} />
      <Route path="/owner/reports" element={G("OWNER", <OwnerReports />)} />
      <Route path="/supplier" element={G("SUPPLIER", <SupplierPage />)} />
      <Route path="/alerts" element={G(null, <AlertsPage />)} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
