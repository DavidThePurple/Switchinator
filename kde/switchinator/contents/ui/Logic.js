// Pure backend helpers: window identity remains valid under both Wayland and X11.
function key(window) { return String(window.internalId); }
function eligible(window) {
    return window && !window.deleted && !window.skipSwitcher && !window.skipTaskbar
        && (window.normalWindow || window.dialog) && !window.excludeFromCapture;
}
function nextOrder(order, windows, custom) {
    var live=windows.map(key);
    var result=order.filter(function(id) { return live.indexOf(id)>=0; });
    if (!custom) live.forEach(function(id) { if (result.indexOf(id)<0) result.push(id); });
    return result;
}
function nextTarget(order, active) {
    if (!order.length) return null;
    var index=order.indexOf(active);
    var target=order[(index+1)%order.length];
    return target===active ? null : target;
}
function append(order, id) { return order.indexOf(id)<0 ? order.concat([id]) : order.slice(); }
function clamp(value, low, high) { return Math.max(low,Math.min(value,high)); }
function contains(rect, point) {
    return point.x>=rect.x && point.y>=rect.y && point.x<rect.x+rect.width && point.y<rect.y+rect.height;
}
function intersects(a,b) {
    return a.x<b.x+b.width && a.x+a.width>b.x && a.y<b.y+b.height && a.y+a.height>b.y;
}
function mix(a,b,t) { return a+(b-a)*t; }
