import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import logoUrl from "../../../../resources/logo_cyrillic.png";
import { text } from "../../i18n/resources";

const methodologyLinks = [
  { to: "/methodology/statements", label: text.nav.methodologyStatements },
  { to: "/methodology/programs", label: text.nav.methodologyPrograms },
  { to: "/methodology/controversial-topics", label: text.nav.methodologyControversialTopics }
];

export function Header() {
  const location = useLocation();
  const isMethodologyActive = location.pathname.startsWith("/methodology");
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <NavLink to="/" className="brand" aria-label={text.app.brand}>
          <img className="brand-logo" src={logoUrl} alt="" aria-hidden="true" />
        </NavLink>
        <nav className="site-nav" aria-label={text.nav.aria}>
          <NavLink to="/parties">{text.nav.parties}</NavLink>
          <NavLink to="/politicians">{text.nav.politicians}</NavLink>
          <NavLink to="/statements">{text.nav.statements}</NavLink>
          <NavLink to="/programs">{text.nav.programs}</NavLink>
          <NavLink to="/dashboard">{text.nav.dashboard}</NavLink>
          <div
            className="nav-dropdown"
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) {
                setIsMethodologyOpen(false);
              }
            }}
            onFocus={() => setIsMethodologyOpen(true)}
            onMouseEnter={() => setIsMethodologyOpen(true)}
            onMouseLeave={() => setIsMethodologyOpen(false)}
          >
            <NavLink
              to="/methodology/statements"
              aria-expanded={isMethodologyOpen}
              aria-haspopup="menu"
              className={({ isActive }) =>
                isActive || isMethodologyActive ? "active nav-dropdown-trigger" : "nav-dropdown-trigger"
              }
            >
              {text.nav.methodology}
            </NavLink>
            <div className={isMethodologyOpen ? "nav-dropdown-menu open" : "nav-dropdown-menu"} role="menu">
              {methodologyLinks.map((item) => (
                <NavLink key={item.to} to={item.to} role="menuitem" onClick={() => setIsMethodologyOpen(false)}>
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
          <NavLink to="/search">{text.nav.search}</NavLink>
        </nav>
      </div>
    </header>
  );
}
