function f(n) {    // Format integers to have at least two digits.
    return n < 10 ? '0' + n : n;
}

Date.prototype.rfc3339 = function() {
    return this.getUTCFullYear()   + '-' +
         f(this.getUTCMonth() + 1) + '-' +
         f(this.getUTCDate())      + 'T' +
         f(this.getUTCHours())     + ':' +
         f(this.getUTCMinutes())   + ':' +
         f(this.getUTCSeconds())   + 'Z';
};

// This is a format that collates in order and tends to work with
// JavaScript's new Date(string) date parsing capabilities, unlike rfc3339.
Date.prototype.toJSON = function() {
    return this.getUTCFullYear()   + '/' +
         f(this.getUTCMonth() + 1) + '/' +
         f(this.getUTCDate())      + ' ' +
         f(this.getUTCHours())     + ':' +
         f(this.getUTCMinutes())   + ':' +
         f(this.getUTCSeconds())   + ' +0000';
};