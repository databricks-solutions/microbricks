import { ApolloClient, InMemoryCache, HttpLink } from "@apollo/client/core";

const httpLink = new HttpLink({
  uri: "/api/graphql",
});

export const apolloClient = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          patients: { keyArgs: ["q"] },
          providers: { keyArgs: ["q", "isActive"] },
          appointments: { keyArgs: ["q", "status", "visitTypeCode", "fromDate", "toDate", "patientQ"] },
          labOrders: { keyArgs: ["q", "status", "patientQ"] },
          prescriptions: { keyArgs: ["patientId", "status"] },
          invoices: { keyArgs: ["patientId", "status", "patientQ"] },
          billingOverview: { keyArgs: ["q", "status", "patientQ"] },
          alerts: { keyArgs: ["q", "severity", "type"] },
          patientSummary: { keyArgs: ["id"] },
          patientTimeline: { keyArgs: ["id"] },
        },
      },
    },
  }),
  defaultOptions: {
    watchQuery: { fetchPolicy: "cache-and-network" },
  },
});
