import heat as ht
from heat.cluster._kcluster import _KCluster


class KMedoids(_KCluster):
    def __init__(self, n_clusters=8, init="random", max_iter=300, random_state=None):
        """
        This is not the original implementation of k-medoids using PAM as originally proposed by ...
        This is kmedoids with the manhattan distance as fixed metric, calculating the median of the assigned cluster points as new cluster center
        and snapping the centroid to the the nearest datapoint afterwards.

        Parameters
        ----------
        n_clusters : int, optional, default: 8
            The number of clusters to form as well as the number of centroids to generate.
        init : {‘random’ or an ndarray}
            Method for initialization, defaults to ‘random’:
            ‘k-medians++’ : selects initial cluster centers for the clustering in a smart way to speed up convergence [2].
            ‘random’: choose k observations (rows) at random from data for the initial centroids.
            If an ht.DNDarray is passed, it should be of shape (n_clusters, n_features) and gives the initial centers.
        max_iter : int, default: 300
            Maximum number of iterations of the k-means algorithm for a single run.
        random_state : int
            Determines random number generation for centroid initialization.

        """
        if init == "kmedians++":
            init = "probability_based"

        super().__init__(
            metric=lambda x, y: ht.spatial.distance.manhattan(x, y, expand=True),
            n_clusters=n_clusters,
            init=init,
            max_iter=max_iter,
            tol=0.0,
            random_state=random_state,
        )

    def _update_centroids(self, X, matching_centroids):
        new_cluster_centers = self._cluster_centers.copy()
        for i in range(self.n_clusters):
            # points in current cluster
            selection = (matching_centroids == i).astype(ht.int64)

            # Remove 0-element lines to avoid spoiling of median
            assigned_points = X * selection
            assigned_points = assigned_points[(assigned_points.abs()).sum(axis=1) != 0]
            median = ht.median(assigned_points, axis=0, keepdim=True)

            # snap Median value to nearest data point
            dist = self._metric(X, median)
            closest_point = X[dist.argmin(axis=0, keepdim=False), :]

            new_cluster_centers[i : i + 1, :] = closest_point

        return new_cluster_centers

    def fit(self, X):
        """
        Computes the centroid of a k-means clustering.

        Parameters
        ----------
        X : ht.DNDarray, shape = [n_samples, n_features]:
            Training instances to cluster.
        """
        # input sanitation
        if not isinstance(X, ht.DNDarray):
            raise ValueError("input needs to be a ht.DNDarray, but was {}".format(type(X)))

        # initialize the clustering
        self._initialize_cluster_centers(X)
        self._n_iter = 0
        matching_centroids = ht.zeros((X.shape[0]), split=X.split, device=X.device, comm=X.comm)
        # iteratively fit the points to the centroids
        for epoch in range(self.max_iter):
            # increment the iteration count
            self._n_iter += 1
            # determine the centroids
            matching_centroids = self._assign_to_cluster(X)

            # update the centroids
            new_cluster_centers = self._update_centroids(X, matching_centroids)

            # check whether centroid movement has converged
            if ht.equal(self._cluster_centers, new_cluster_centers):
                break
            self._cluster_centers = new_cluster_centers.copy()

        self._labels = matching_centroids

        return self