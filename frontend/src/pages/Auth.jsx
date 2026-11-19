import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { HOME, useAuth } from "../auth";
import { act, Field, toast } from "../ui";

const ROLES = [["OWNER", "Shop Owner"], ["SUPPLIER", "Supplier"]];

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [role, setRole] = useState("OWNER");
  const [f, setF] = useState({ email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = await login(f.email, f.password, role);
      nav(HOME[u.role]);
    } catch {
      toast("Invalid email, password or role.", "danger");
    }
    setBusy(false);
  };
  return (
    <div className="container py-5" style={{ maxWidth: 420 }}>
      <div className="text-center mb-4"><i className="bi bi-box-seam fs-1 text-primary" /><h3>SmartStock</h3><div className="text-muted">Supplier and Shop Owner: Inventory, Reorder and Payment</div></div>
      <div className="btn-group w-100 mb-3">{ROLES.map(([r, l]) => <button key={r} type="button" className={`btn btn-${role === r ? "primary" : "outline-primary"}`} onClick={() => setRole(r)}>{l}</button>)}</div>
      <form className="card card-body" onSubmit={submit}>
        <Field label="Email"><input type="email" required className="form-control" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Password"><input type="password" required className="form-control" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <button className="btn btn-primary w-100" disabled={busy}>{busy ? "Signing in..." : "Login"}</button>
        <div className="text-center mt-3 small">New here? <Link to="/register">Create an account</Link></div>
      </form>
      <div className="small text-muted text-center mt-3">Demo: owner1@demo.com or supplier1@demo.com, password Demo@12345</div>
    </div>
  );
}

export function Register() {
  const nav = useNavigate();
  const [role, setRole] = useState("OWNER");
  const [f, setF] = useState({});
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const inp = (k, label, type = "text", req = true) => <Field label={label}><input type={type} required={req} className="form-control" onChange={set(k)} /></Field>;
  const submit = (e) => {
    e.preventDefault();
    act(() => api.post(`/auth/register/${role.toLowerCase()}/`, f), "Registered! Please login.", () => nav("/login"));
  };
  return (
    <div className="container py-4" style={{ maxWidth: 560 }}>
      <h4 className="text-center mb-3">Create account</h4>
      <div className="btn-group w-100 mb-3">{ROLES.map(([r, l]) => <button key={r} type="button" className={`btn btn-${role === r ? "primary" : "outline-primary"}`} onClick={() => { setRole(r); setF({}); }}>{l}</button>)}</div>
      <form className="card card-body" onSubmit={submit} key={role}>
        {role === "OWNER" ? <>
          {inp("owner_name", "Owner name")}{inp("email", "Email", "email")}{inp("phone", "Phone", "tel", false)}{inp("password", "Password (8+ characters, letters and digits)", "password")}
          {inp("shop_name", "Shop name")}{inp("shop_address", "Shop address")}{inp("city", "City", "text", false)}
        </> : <>
          {inp("company_name", "Company name")}{inp("contact_person", "Contact person", "text", false)}{inp("email", "Email", "email")}{inp("phone", "Phone", "tel", false)}
          {inp("password", "Password (8+ characters, letters and digits)", "password")}{inp("address", "Address", "text", false)}
        </>}
        <button className="btn btn-primary">Register</button>
        <div className="text-center mt-3 small"><Link to="/login">Back to login</Link></div>
      </form>
    </div>
  );
}
