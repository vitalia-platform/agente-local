import { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Activity, Server, List, Settings, LogOut } from 'lucide-react';
import styles from './Layout.module.css';

export function Layout({ children }: { children: React.ReactNode }) {
  const { logout } = useContext(AuthContext);

  const navItems = [
    { to: "/", icon: <Activity size={20} />, label: "Telemetry" },
    { to: "/nodes", icon: <Server size={20} />, label: "Nodes" },
    { to: "/queues", icon: <List size={20} />, label: "Queues" },
    { to: "/settings", icon: <Settings size={20} />, label: "Settings" },
  ];

  return (
    <div className={styles.appContainer}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <h2>Vitalia Pro</h2>
        </div>
        <nav className={styles.nav}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => 
                isActive ? `${styles.navItem} ${styles.active}` : styles.navItem
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className={styles.footer}>
          <button className={styles.logoutBtn} onClick={logout}>
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
}
