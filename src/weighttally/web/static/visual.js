function renderVisual(target, data) {
    const counts = new Map(data.flow_counts);
    const posted = counts.get('已分派') ?? 0;
    const deferred = counts.get('候补') ?? 0;
    const isolation = counts.get('暂停') ?? 0;
    const figure = node('div',undefined,'coupon');
    const values = node('dl',undefined,'receipt-lines');
    const charges = {'本班称签':data.rows.length,'安排复秤':posted,'复秤候补':deferred,'扣皮码暂停':isolation};
    Object.entries(charges).forEach(([label,count]) => values.append(node('dt',label),node('dd',count)));
    figure.append(values,node('p',`称签校验码 ${data.sample_hash.slice(0,16)}`,'checksum'));
    target.append(figure);
}
