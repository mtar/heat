import sys

import heat as ht


class GaussianNB:
        """
    Gaussian Naive Bayes (GaussianNB)
    Can perform online updates to model parameters via :meth:`partial_fit`.
    For details on algorithm used to update feature means and variance online,
    see Stanford CS tech report STAN-CS-79-773 by Chan, Golub, and LeVeque:
        http://i.stanford.edu/pub/cstr/reports/cs/tr/79/773/CS-TR-79-773.pdf
    Read more in the :ref:`User Guide <gaussian_naive_bayes>`.
    Parameters
    ----------
    priors : array-like, shape (n_classes,)
        Prior probabilities of the classes. If specified the priors are not
        adjusted according to the data.
    var_smoothing : float, optional (default=1e-9)
        Portion of the largest variance of all features that is added to
        variances for calculation stability.
    Attributes
    ----------
    class_count_ : array, shape (n_classes,)
        number of training samples observed in each class.
    class_prior_ : array, shape (n_classes,)
        probability of each class.
    classes_ : array, shape (n_classes,)
        class labels known to the classifier
    epsilon_ : float
        absolute additive value to variances
    sigma_ : array, shape (n_classes, n_features)
        variance of each feature per class
    theta_ : array, shape (n_classes, n_features)
        mean of each feature per class
    Examples
    --------
    >>> import numpy as np
    >>> X = np.array([[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]])
    >>> Y = np.array([1, 1, 1, 2, 2, 2])
    >>> from sklearn.naive_bayes import GaussianNB
    >>> clf = GaussianNB()
    >>> clf.fit(X, Y)
    GaussianNB()
    >>> print(clf.predict([[-0.8, -1]]))
    [1]
    >>> clf_pf = GaussianNB()
    >>> clf_pf.partial_fit(X, Y, np.unique(Y))
    GaussianNB()
    >>> print(clf_pf.predict([[-0.8, -1]]))
    [1]
    """

    def __init__(self, priors=None, var_smoothing=1e-9):
        self.priors = priors
        self.var_smoothing = var_smoothing

    def fit(self, X, y, sample_weight=None):
        """Fit Gaussian Naive Bayes according to X, y
        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            Training vectors, where n_samples is the number of samples
            and n_features is the number of features.
        y : array-like, shape (n_samples,)
            Target values.
        sample_weight : array-like, shape (n_samples,), optional (default=None)
            Weights applied to individual samples (1. for unweighted).
            .. versionadded:: 0.17
               Gaussian Naive Bayes supports fitting with *sample_weight*.
        Returns
        -------
        self : object
        """
        #sanitize input 
        if not isinstance(X, ht.DNDarray):
            raise ValueError("input needs to be a ht.DNDarray, but was {}".format(type(X)))
        if not isinstance(y, ht.DNDarray):
            raise ValueError("input needs to be a ht.DNDarray, but was {}".format(type(y)))
        if y.numdims != 1:
            raise ValueError("expected y to be a 1-D tensor, is {}-D".format(y.numdims))
        if sample_weight is not None:
            if not isinstance(sample_weight, ht.DNDarray):
                raise ValueError("sample_weight needs to be a ht.DNDarray, but was {}".format(type(sample_weight)))
        return self._partial_fit(X, y, ht.unique(y), _refit=True,
                                 sample_weight=sample_weight)

    @staticmethod
    def _check_partial_fit_first_call(clf, classes=None):
    """Private helper function for factorizing common classes param logic
    Estimators that implement the ``partial_fit`` API need to be provided with
    the list of possible classes at the first call to partial_fit.
    Subsequent calls to partial_fit should check that ``classes`` is still
    consistent with a previous value of ``clf.classes_`` when provided.
    This function returns True if it detects that this was the first call to
    ``partial_fit`` on ``clf``. In that case the ``classes_`` attribute is also
    set on ``clf``.
    """
    if getattr(clf, 'classes_', None) is None and classes is None:
        raise ValueError("classes must be passed on the first call "
                         "to partial_fit.")

    elif classes is not None:
        unique_labels = ht.sort(classes)[0]
        if getattr(clf, 'classes_', None) is not None:
            if not ht.equal(clf.classes_, unique_labels): #TODO: unique_labels
                raise ValueError(
                    "`classes=%r` is not the same as on last call "
                    "to partial_fit, was: %r" % (classes, clf.classes_))

        else:
            # This is the first call to partial_fit
            clf.classes_ = unique_labels
            return True

    # classes is None and clf.classes_ has already previously been set:
    # nothing to do
    return False

    @staticmethod
    def _update_mean_variance(n_past, mu, var, X, sample_weight=None):
        """Compute online update of Gaussian mean and variance.
        Given starting sample count, mean, and variance, a new set of
        points X, and optionally sample weights, return the updated mean and
        variance. (NB - each dimension (column) in X is treated as independent
        -- you get variance, not covariance).
        Can take scalar mean and variance, or vector mean and variance to
        simultaneously update a number of independent Gaussians.
        See Stanford CS tech report STAN-CS-79-773 by Chan, Golub, and LeVeque:
        http://i.stanford.edu/pub/cstr/reports/cs/tr/79/773/CS-TR-79-773.pdf
        Parameters
        ----------
        n_past : int
            Number of samples represented in old mean and variance. If sample
            weights were given, this should contain the sum of sample
            weights represented in old mean and variance.
        mu : array-like, shape (number of Gaussians,)
            Means for Gaussians in original set.
        var : array-like, shape (number of Gaussians,)
            Variances for Gaussians in original set.
        sample_weight : array-like, shape (n_samples,), optional (default=None)
            Weights applied to individual samples (1. for unweighted).
        Returns
        -------
        total_mu : array-like, shape (number of Gaussians,)
            Updated mean for each Gaussian over the combined set.
        total_var : array-like, shape (number of Gaussians,)
            Updated variance for each Gaussian over the combined set.
        """
        if X.shape[0] == 0:
            return mu, var

        # Compute (potentially weighted) mean and variance of new datapoints
        if sample_weight is not None:
            n_new = float(sample_weight.sum())
            new_mu = ht.average(X, axis=0, weights=sample_weight) #TODO: check out Issue #351
            new_var = ht.average((X - new_mu) ** 2, axis=0,
                                 weights=sample_weight)
        else:
            n_new = X.shape[0]
            new_var = ht.var(X, axis=0)
            new_mu = ht.mean(X, axis=0)

        if n_past == 0:
            return new_mu, new_var

        n_total = float(n_past + n_new)

        # Combine mean of old and new data, taking into consideration
        # (weighted) number of observations
        total_mu = (n_new * new_mu + n_past * mu) / n_total

        # Combine variance of old and new data, taking into consideration
        # (weighted) number of observations. This is achieved by combining
        # the sum-of-squared-differences (ssd)
        old_ssd = n_past * var
        new_ssd = n_new * new_var
        total_ssd = (old_ssd + new_ssd +
                     (n_new * n_past / n_total) * (mu - new_mu) ** 2)
        total_var = total_ssd / n_total

        return total_mu, total_var

    def partial_fit(self, X, y, classes=None, sample_weight=None):
        """Incremental fit on a batch of samples.
        This method is expected to be called several times consecutively
        on different chunks of a dataset so as to implement out-of-core
        or online learning.
        This is especially useful when the whole dataset is too big to fit in
        memory at once.
        This method has some performance and numerical stability overhead,
        hence it is better to call partial_fit on chunks of data that are
        as large as possible (as long as fitting in the memory budget) to
        hide the overhead.
        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            Training vectors, where n_samples is the number of samples and
            n_features is the number of features.
        y : array-like, shape (n_samples,)
            Target values.
        classes : array-like, shape (n_classes,), optional (default=None)
            List of all the classes that can possibly appear in the y vector.
            Must be provided at the first call to partial_fit, can be omitted
            in subsequent calls.
        sample_weight : array-like, shape (n_samples,), optional (default=None)
            Weights applied to individual samples (1. for unweighted).
            .. versionadded:: 0.17
        Returns
        -------
        self : object
        """
        return self._partial_fit(X, y, classes, _refit=False,
                                 sample_weight=sample_weight)

    def _partial_fit(self, X, y, classes=None, _refit=False,
                     sample_weight=None):
        """Actual implementation of Gaussian NB fitting.
        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            Training vectors, where n_samples is the number of samples and
            n_features is the number of features.
        y : array-like, shape (n_samples,)
            Target values.
        classes : array-like, shape (n_classes,), optional (default=None)
            List of all the classes that can possibly appear in the y vector.
            Must be provided at the first call to partial_fit, can be omitted
            in subsequent calls.
        _refit : bool, optional (default=False)
            If true, act as though this were the first time we called
            _partial_fit (ie, throw away any past fitting and start over).
        sample_weight : array-like, shape (n_samples,), optional (default=None)
            Weights applied to individual samples (1. for unweighted).
        Returns
        -------
        self : object
        """
        #sanitize X and y shape
        n_samples = X.shape[0]
        if X.numdims != 2:
            raise ValueError("expected X to be a 2-D tensor, is {}-D".format(X.numdims))
        if y.shape[0] != n_samples:
            raise ValueError("y.shape[0] must match number of samples {}, is {}".format(n_samples, y.shape[0]))
        #TODO: more complex checks might be needed, see sklearn.utils.validation.check_X_y()
        if sample_weight is not None:
            #sanitize shape of weights
            if sample_weight.numdims != 1:
                raise ValueError("Sample weights must be 1D tensor")
            if sample_weight.shape != (n_samples,):
                raise ValueError("sample_weight.shape == {}, expected {}!"
                             .format(sample_weight.shape, (n_samples,)))

        #TODO possibly deeper checks needed, see sklearn.utils.validation._check_sample_weight
        #sample_weight = _check_sample_weight(sample_weight, X) 
        
        # If the ratio of data variance between dimensions is too small, it
        # will cause numerical errors. To address this, we artificially
        # boost the variance by epsilon, a small fraction of the standard
        # deviation of the largest dimension.
        self.epsilon_ = self.var_smoothing * ht.var(X, axis=0).max()

        if _refit:
            self.classes_ = None

        if _check_partial_fit_first_call(self, classes):
            # This is the first call to partial_fit:
            # initialize various cumulative counters
            n_features = X.shape[1]
            n_classes = len(self.classes_)
            self.theta_ = ht.zeros((n_classes, n_features))
            self.sigma_ = ht.zeros((n_classes, n_features))

            self.class_count_ = ht.zeros(n_classes, dtype=ht.float64)

            # Initialise the class prior
            # Take into account the priors
            if self.priors is not None:
                priors = ht.asarray(self.priors)
                # Check that the provide prior match the number of classes
                if len(priors) != n_classes:
                    raise ValueError('Number of priors must match number of'
                                     ' classes.')
                # Check that the sum is 1
                if not ht.isclose(priors.sum(), 1.0):
                    raise ValueError('The sum of the priors should be 1.')
                # Check that the prior are non-negative
                if (priors < 0).any():
                    raise ValueError('Priors must be non-negative.')
                self.class_prior_ = priors
            else:
                # Initialize the priors to zeros for each class
                self.class_prior_ = ht.zeros(len(self.classes_),
                                             dtype=ht.float64)
        else:
            if X.shape[1] != self.theta_.shape[1]:
                msg = "Number of features %d does not match previous data %d."
                raise ValueError(msg % (X.shape[1], self.theta_.shape[1]))
            # Put epsilon back in each time
            self.sigma_[:, :] -= self.epsilon_

        classes = self.classes_

        unique_y = ht.unique(y)
        unique_y_in_classes = ht.in1d(unique_y, classes) #TODO nt.in1d

        if not ht.all(unique_y_in_classes):
            raise ValueError("The target label(s) %s in y do not exist in the "
                             "initial classes %s" %
                             (unique_y[~unique_y_in_classes], classes))

        for y_i in unique_y:
            i = classes.searchsorted(y_i)
            X_i = X[y == y_i, :]

            if sample_weight is not None:
                sw_i = sample_weight[y == y_i]
                N_i = sw_i.sum()
            else:
                sw_i = None
                N_i = X_i.shape[0]

            new_theta, new_sigma = self._update_mean_variance(
                self.class_count_[i], self.theta_[i, :], self.sigma_[i, :],
                X_i, sw_i)

            self.theta_[i, :] = new_theta
            self.sigma_[i, :] = new_sigma
            self.class_count_[i] += N_i

        self.sigma_[:, :] += self.epsilon_

        # Update if only no priors is provided
        if self.priors is None:
            # Empirical prior, with sample_weight taken into account
            self.class_prior_ = self.class_count_ / self.class_count_.sum()

        return self

    def _joint_log_likelihood(self, X):
        joint_log_likelihood = []
        for i in range(ht.size(self.classes_)):
            jointi = ht.log(self.class_prior_[i])
            n_ij = - 0.5 * ht.sum(ht.log(2. * ht.pi * self.sigma_[i, :]))
            n_ij -= 0.5 * ht.sum(((X - self.theta_[i, :]) ** 2) /
                                 (self.sigma_[i, :]), 1)
            joint_log_likelihood.append(jointi + n_ij)

        joint_log_likelihood = ht.array(joint_log_likelihood).T
        return joint_log_likelihood


