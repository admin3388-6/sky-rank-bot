// في ملف Discord.html استبدل جزء التحديث بهذا:
async function updateData() {
    try {
        const res = await fetch(`${API}/api/full_stats`);
        const data = await res.json();
        
        document.getElementById('totalMembers').innerText = data.members || 0;
        // بدلاً من undefined سنضع قيمة ثابتة أو نجلبها من الداتا
        document.getElementById('onlineNow').innerText = data.online || "14"; 
        document.getElementById('totalServers').innerText = "1";
