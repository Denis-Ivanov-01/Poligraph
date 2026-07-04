import { NavLink } from "react-router-dom";
import { text } from "../../i18n/resources";

export function Header() {
  return (
    <header className="site-header">
      <NavLink to="/" className="brand">
        {text.app.brand}
      </NavLink>
      <nav className="site-nav" aria-label={text.nav.aria}>
        <NavLink to="/parties">{text.nav.parties}</NavLink>
        <NavLink to="/politicians">{text.nav.politicians}</NavLink>
        <NavLink to="/statements">{text.nav.statements}</NavLink>
        <NavLink to="/dashboard">{text.nav.dashboard}</NavLink>
        <NavLink to="/search">{text.nav.search}</NavLink>
      </nav>
    </header>
  );
}
