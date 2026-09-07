function boundary_is_inside(container, node) {
    if (!container || !node) { return false }
    const boundary_element = node.nodeType === Node.TEXT_NODE ? node.parentNode : node
    return boundary_element === container || container.contains(boundary_element)
}

export function get_selection_offsets(container, range) {
    if (!range
        || !boundary_is_inside(container, range.startContainer)
        || !boundary_is_inside(container, range.endContainer)) {
        return null
    }

    const prefix = range.cloneRange()
    prefix.selectNodeContents(container)
    prefix.setEnd(range.startContainer, range.startOffset)
    const start = prefix.toString().length

    prefix.setEnd(range.endContainer, range.endOffset)
    const end = prefix.toString().length

    return [start, end]
}
