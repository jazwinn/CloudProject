export function getDefaultColor(index) {
  const colors = ['#ffffff', '#aaaaaa', '#85B7EB', '#5DCAA5', '#F0997B', '#AFA9EC', '#ED93B1', '#FAC775'];
  return colors[index % colors.length];
}

export function generateColorsForClusters(clusterList) {
    const colors = ['#85B7EB', '#5DCAA5', '#F0997B', '#AFA9EC', '#ED93B1', '#FAC775'];
    return clusterList.map((c, i) => ({
        ...c,
        color: colors[i % colors.length]
    }));
}
