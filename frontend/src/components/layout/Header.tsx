import { NavLink } from "react-router-dom";
import { text } from "../../i18n/resources";

export function Header() {
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <NavLink to="/" className="brand" aria-label={text.app.brand}>
          <span className="brand-mark" aria-hidden="true" />
          <span>{text.app.brand}</span>
        </NavLink>
        <nav className="site-nav" aria-label={text.nav.aria}>
          <NavLink to="/parties">{text.nav.parties}</NavLink>
          <NavLink to="/politicians">{text.nav.politicians}</NavLink>
          <NavLink to="/statements">{text.nav.statements}</NavLink>
          <NavLink to="/programs">{text.nav.programs}</NavLink>
          <NavLink to="/dashboard">{text.nav.dashboard}</NavLink>
          <NavLink to="/methodology">{text.nav.methodology}</NavLink>
          <NavLink to="/search">{text.nav.search}</NavLink>
        </nav>
      </div>
    </header>
  );
}
