import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { GlassPanel } from '../components/GlassPanel';
import styles from './Inventory.module.css';

interface NodeInfo {
  node_id: string;
  ip_address: string;
  status: string;
  models?: string;
  [key: string]: any;
}

export function Inventory() {
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const { data } = await apiClient.get('/nodes');
        setNodes(data.nodes || []);
      } catch (err) {
        console.error('Failed to fetch nodes', err);
      } finally {
        setLoading(false);
      }
    };
    fetchNodes();
  }, []);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Node Inventory</h1>
      <p className={styles.subtitle}>Discover and manage connected compute nodes</p>
      
      {loading ? (
        <p>Loading nodes...</p>
      ) : nodes.length === 0 ? (
        <GlassPanel>
          <p className={styles.empty}>No nodes found in the network.</p>
        </GlassPanel>
      ) : (
        <div className={styles.grid}>
          {nodes.map(node => (
            <GlassPanel key={node.node_id} className={styles.nodeCard}>
              <div className={styles.nodeHeader}>
                <h3>{node.node_id}</h3>
                <span className={`${styles.status} ${styles[node.status?.toLowerCase()] || ''}`}>
                  {node.status || 'UNKNOWN'}
                </span>
              </div>
              <div className={styles.nodeBody}>
                <p><strong>IP:</strong> {node.ip_address || 'N/A'}</p>
                {node.models && <p><strong>Models:</strong> {node.models}</p>}
                <pre className={styles.rawJson}>
                  {JSON.stringify(node, null, 2)}
                </pre>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}
    </div>
  );
}
