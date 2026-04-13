import { useEffect, useState } from "react";
import { getOrders, confirmOrder } from "./api";

export default function Dashboard() {
  const [orders, setOrders] = useState([]);
  const token = localStorage.getItem("token");

  const load = async () => {
    const res = await getOrders(token);
    setOrders(res.data);
  };

  const confirm = async (id) => {
    await confirmOrder(id, token);
    load();
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <h2>Orders</h2>
      {orders.map(o => (
        <div key={o.id}>
          #{o.id} - {o.status}
          {o.status === "pending" && (
            <button onClick={() => confirm(o.id)}>Confirm</button>
          )}
        </div>
      ))}
    </div>
  );
}
