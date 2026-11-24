export const ISSUE_TYPES = {
    omission: 'Missing meaning',
    uncertain_source: 'Unclear source meaning',
    other: 'Other',
};

export function validAnnotationIssue(issue) {
    return typeof issue?.category === 'string' && Object.hasOwn(ISSUE_TYPES, issue.category) && typeof issue.note === 'string';
}
