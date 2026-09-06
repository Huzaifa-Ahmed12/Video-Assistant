import { Link, NavLink } from "react-router-dom";
import "./Navbar.css";

export default function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo">
        Video Assistant
      </Link>
      <div className="navbar-links">
        <NavLink 
          to="/" 
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          end
        >
          Upload
        </NavLink>
        <NavLink 
          to="/meetings" 
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          Meetings
        </NavLink>
      </div>
    </nav>
  );
}
